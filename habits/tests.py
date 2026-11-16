from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch
from .models import Evidencia, Habit, HabitLog, HabitPadrino
from .services import MAX_UPLOAD_SIZE, calcular_racha_actual, generar_presigned_url_s3


class HabitCustomFrequencyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='custom-frequency-owner', password='test-password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def test_create_custom_frequency_persists_selected_days(self):
        today = timezone.localdate()
        custom_days = sorted({(today.weekday() + 1) % 7})
        response = self.client.post(
            '/api/v1/habits/',
            {
                'name': 'Ejercicio',
                'frequency': Habit.FrequencyType.CUSTOM,
                'custom_days': custom_days,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['custom_days'], custom_days)
        self.assertFalse(response.data['is_scheduled_today'])
        self.assertEqual(
            Habit.objects.get(id=response.data['id']).custom_days,
            custom_days,
        )

    def test_cannot_create_log_on_unscheduled_day(self):
        today = timezone.localdate()
        habit = Habit.objects.create(
            user=self.owner,
            name='Ejercicio',
            frequency=Habit.FrequencyType.CUSTOM,
            custom_days=[(today.weekday() + 1) % 7],
        )

        response = self.client.post(
            '/api/v1/logs/',
            {'habit': habit.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date', response.data)
        self.assertFalse(HabitLog.objects.filter(habit=habit).exists())

    def test_weekdays_and_weekends_reject_logs_outside_their_schedule(self):
        today = timezone.localdate()
        saturday = today + timedelta(days=(5 - today.weekday()) % 7)
        monday = today + timedelta(days=(7 - today.weekday()) % 7 or 7)

        for frequency, log_date in (
            (Habit.FrequencyType.WEEKDAYS, saturday),
            (Habit.FrequencyType.WEEKENDS, monday),
        ):
            with self.subTest(frequency=frequency):
                habit = Habit.objects.create(
                    user=self.owner,
                    name=f'Hábito {frequency}',
                    frequency=frequency,
                )
                response = self.client.post(
                    '/api/v1/logs/',
                    {'habit': habit.id, 'date': log_date.isoformat()},
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('date', response.data)

    def test_existing_log_cannot_be_retried_on_unscheduled_day(self):
        today = timezone.localdate()
        habit = Habit.objects.create(
            user=self.owner,
            name='Ejercicio',
            frequency=Habit.FrequencyType.CUSTOM,
            custom_days=[(today.weekday() + 1) % 7],
        )
        existing_log = HabitLog.objects.create(
            habit=habit,
            date=today,
            estado=HabitLog.Estado.RECHAZADO,
        )

        response = self.client.post(
            '/api/v1/logs/',
            {'habit': habit.id, 'date': today.isoformat()},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        existing_log.refresh_from_db()
        self.assertEqual(existing_log.estado, HabitLog.Estado.RECHAZADO)

    def test_custom_frequency_requires_distinct_valid_days(self):
        for custom_days in ([], [7], [1, 1]):
            with self.subTest(custom_days=custom_days):
                response = self.client.post(
                    '/api/v1/habits/',
                    {
                        'name': 'Ejercicio',
                        'frequency': Habit.FrequencyType.CUSTOM,
                        'custom_days': custom_days,
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('custom_days', response.data)

    def test_custom_streak_skips_unselected_days(self):
        today = timezone.localdate()
        custom_days = sorted({today.weekday(), (today.weekday() - 2) % 7})
        habit = Habit.objects.create(
            user=self.owner,
            name='Ejercicio',
            frequency=Habit.FrequencyType.CUSTOM,
            custom_days=custom_days,
        )
        for days_ago in (0, 2):
            HabitLog.objects.create(
                habit=habit,
                date=today - timedelta(days=days_ago),
                estado=HabitLog.Estado.APROBADO,
            )

        self.assertEqual(calcular_racha_actual(habit), 2)


class HabitLogCreateTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='habit-owner', password='test-password')
        self.habit = Habit.objects.create(user=self.owner, name='Leer')
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def test_create_log_without_accepted_sponsor_approves_automatically(self):
        response = self.client.post(
            '/api/v1/logs/',
            {'habit': self.habit.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], HabitLog.Estado.APROBADO)

    def test_create_log_with_accepted_sponsor_enters_review(self):
        sponsor = User.objects.create_user(username='habit-sponsor', password='test-password')
        HabitPadrino.objects.create(
            habit=self.habit,
            padrino=sponsor,
            estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO,
        )

        response = self.client.post(
            '/api/v1/logs/',
            {'habit': self.habit.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['estado'], HabitLog.Estado.EN_REVISION)

    def test_create_log_returns_existing_log_for_same_habit_and_date(self):
        existing_log = HabitLog.objects.create(
            habit=self.habit,
            estado=HabitLog.Estado.RECHAZADO,
        )

        response = self.client.post(
            '/api/v1/logs/',
            {'habit': self.habit.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], existing_log.id)
        self.assertEqual(response.data['estado'], HabitLog.Estado.RECHAZADO)


class PresignedURLTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='upload-user', password='test-password')
        self.client = APIClient()
        self.client.force_authenticate(user=user)

    def test_rejects_unsupported_mime_type(self):
        response = self.client.post(
            '/api/v1/s3/presigned-url/',
            {'file_name': 'evidence.txt', 'file_type': 'text/plain'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file_type', response.data)

    def test_accepts_allowed_mime_types(self):
        for file_type in ('image/jpeg', 'image/png', 'video/mp4'):
            with self.subTest(file_type=file_type):
                with patch('habits.views.generar_presigned_url_s3', return_value={'upload_url': 'url'}):
                    response = self.client.post(
                        '/api/v1/s3/presigned-url/',
                        {'file_name': 'evidence', 'file_type': file_type},
                        format='json',
                    )

                self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('habits.services.boto3.client')
    def test_signs_exact_content_type_and_maximum_size(self, mock_boto_client):
        mock_boto_client.return_value.generate_presigned_post.return_value = {
            'url': 'https://s3.example.test',
            'fields': {'Content-Type': 'image/png'},
        }

        result = generar_presigned_url_s3('evidence.png', 'image/png')

        self.assertEqual(result['upload_url'], 'https://s3.example.test')
        self.assertEqual(result['fields'], {'Content-Type': 'image/png'})
        mock_boto_client.return_value.generate_presigned_post.assert_called_once()
        kwargs = mock_boto_client.return_value.generate_presigned_post.call_args.kwargs
        self.assertEqual(kwargs['Fields'], {'Content-Type': 'image/png'})
        self.assertIn({'Content-Type': 'image/png'}, kwargs['Conditions'])
        self.assertIn(['content-length-range', 0, MAX_UPLOAD_SIZE], kwargs['Conditions'])


class EvidenciaCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='evidence-user', password='test-password')
        habit = Habit.objects.create(user=self.user, name='Leer')
        self.log = HabitLog.objects.create(habit=habit)
        self.evidence = Evidencia.objects.create(
            habit_log=self.log,
            usuario=self.user,
            s3_file_url='https://bucket.example.test/evidencias/old.png',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_replaces_existing_evidence_for_log(self):
        response = self.client.post(
            '/api/v1/evidencias/',
            {
                'habit_log': self.log.id,
                's3_file_url': 'https://bucket.example.test/evidencias/new.png',
                'descripcion': 'Nueva evidencia',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.evidence.id)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.s3_file_url, 'https://bucket.example.test/evidencias/new.png')


class HabitPadrinoMisSolicitudesTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='invitation-owner', password='test-password')
        self.sponsor = User.objects.create_user(username='invitation-sponsor', password='test-password')
        habit = Habit.objects.create(user=self.owner, name='Caminar')
        self.pending = HabitPadrino.objects.create(
            habit=habit,
            padrino=self.sponsor,
            estado_invitacion=HabitPadrino.EstadoInvitacion.PENDIENTE,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.sponsor)

    def test_mis_solicitudes_only_returns_pending_invitations(self):
        accepted = HabitPadrino.objects.create(
            habit=Habit.objects.create(user=self.owner, name='Meditar'),
            padrino=self.sponsor,
            estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO,
        )

        response = self.client.get('/api/v1/padrinazgos/mis-solicitudes/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in response.data], [self.pending.id])
        self.assertNotIn(accepted.id, [item['id'] for item in response.data])

    def test_accepted_invitation_stays_accepted_and_disappears_after_reload(self):
        update_response = self.client.patch(
            f'/api/v1/padrinazgos/{self.pending.id}/',
            {'estado_invitacion': HabitPadrino.EstadoInvitacion.ACEPTADO},
            format='json',
        )

        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.estado_invitacion, HabitPadrino.EstadoInvitacion.ACEPTADO)

        list_response = self.client.get('/api/v1/padrinazgos/mis-solicitudes/')

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data, [])


class HabitPadrinoInvitationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='habit-owner-invite', password='test-password')
        self.sponsor = User.objects.create_user(username='habit-sponsor-invite', password='test-password')
        self.habit = Habit.objects.create(user=self.owner, name='Ejercicio')
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def test_resending_rejected_invitation_reactivates_existing_relationship(self):
        rejected_invitation = HabitPadrino.objects.create(
            habit=self.habit,
            padrino=self.sponsor,
            estado_invitacion=HabitPadrino.EstadoInvitacion.RECHAZADO,
        )

        response = self.client.post(
            '/api/v1/padrinazgos/',
            {'habit': self.habit.id, 'padrino': self.sponsor.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], rejected_invitation.id)
        self.assertEqual(response.data['estado_invitacion'], HabitPadrino.EstadoInvitacion.PENDIENTE)
        self.assertEqual(HabitPadrino.objects.filter(habit=self.habit).count(), 1)

    def test_rejected_invitations_do_not_count_toward_padrino_limit(self):
        rejected_sponsors = [
            User.objects.create_user(username=f'rejected-sponsor-{index}', password='test-password')
            for index in range(2)
        ]
        for sponsor in rejected_sponsors:
            HabitPadrino.objects.create(
                habit=self.habit,
                padrino=sponsor,
                estado_invitacion=HabitPadrino.EstadoInvitacion.RECHAZADO,
            )

        response = self.client.post(
            '/api/v1/padrinazgos/',
            {'habit': self.habit.id, 'padrino': self.sponsor.id},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            HabitPadrino.objects.filter(
                habit=self.habit,
                estado_invitacion__in=[
                    HabitPadrino.EstadoInvitacion.PENDIENTE,
                    HabitPadrino.EstadoInvitacion.ACEPTADO,
                ],
            ).count(),
            1,
        )

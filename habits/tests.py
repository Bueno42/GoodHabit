from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient
from .models import Habit, HabitLog, HabitPadrino


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

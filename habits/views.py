from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Habit, HabitLog, HabitPadrino
from .serializers import HabitSerializer, HabitLogSerializer, HabitPadrinoSerializer

class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='invitar-padrino')
    def invitar_padrino(self, request, pk=None):
        habito = self.get_object()  # 404 si el hábito no pertenece al usuario autenticado

        padrino_id = request.data.get('padrino_id')
        if not padrino_id:
            return Response({'error': 'Debe proporcionar padrino_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            usuario_padrino = User.objects.get(pk=padrino_id)
        except User.DoesNotExist:
            return Response({'error': 'El usuario especificado no existe.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            asignacion = HabitPadrino.objects.create(
                habit=habito,
                padrino=usuario_padrino
            )
        except ValidationError as e:
            return Response({'error': e.messages}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Este usuario ya fue asignado a este hábito.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HabitPadrinoSerializer(asignacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        habit = self.get_object()
        today = timezone.localdate()
        
        actual_value = request.data.get('actual_value', habit.target_value)
        completed = request.data.get('completed', True)
        notes = request.data.get('notes', '')

        log, created = HabitLog.objects.update_or_create(
            habit=habit,
            date=today,
            defaults={
                'completed': completed,
                'actual_value': actual_value,
                'notes': notes
            }
        )

        serializer = HabitLogSerializer(log)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


class HabitPadrinoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HabitPadrinoSerializer

    def get_queryset(self):
        # Aislamiento: solo las invitaciones dirigidas al usuario en sesión
        return HabitPadrino.objects.filter(padrino=self.request.user)

    @action(detail=False, methods=['get'], url_path='mis-solicitudes')
    def mis_solicitudes(self, request):
        solicitudes = self.get_queryset().filter(
            estado_invitacion=HabitPadrino.EstadoInvitacion.PENDIENTE
        )
        data = [
            {
                'id': s.id,
                'habito_id': s.habit.id,
                'habito_nombre': s.habit.name,
                'creador': s.habit.user.username if s.habit.user else 'Sistema',
                'fecha_asignacion': s.fecha_asignacion
            }
            for s in solicitudes
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='responder')
    def responder(self, request, pk=None):
        asignacion = self.get_object()  # Valida automáticamente pertenencia por get_queryset

        nuevo_estado = request.data.get('estado')
        if nuevo_estado not in [HabitPadrino.EstadoInvitacion.ACEPTADO, HabitPadrino.EstadoInvitacion.RECHAZADO]:
            return Response(
                {'error': 'Estado no válido. Use ACEPTADO o RECHAZADO.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if asignacion.estado_invitacion != HabitPadrino.EstadoInvitacion.PENDIENTE:
            return Response(
                {'error': 'Esta invitación ya fue respondida.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        asignacion.estado_invitacion = nuevo_estado
        asignacion.save()

        return Response(
            {'mensaje': f'Invitación respondida exitosamente como {nuevo_estado}.'},
            status=status.HTTP_200_OK
        )


class HabitLogViewSet(viewsets.ModelViewSet):
    serializer_class = HabitLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HabitLog.objects.filter(habit__user=self.request.user)
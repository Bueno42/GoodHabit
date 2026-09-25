from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Habit, HabitLog
from .serializers import HabitSerializer, HabitLogSerializer

class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Cada usuario solo ve sus hábitos
        return Habit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Asocia automáticamente el hábito al usuario que hizo el request
        serializer.save(user=self.request.user)

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


class HabitLogViewSet(viewsets.ModelViewSet):
    serializer_class = HabitLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Solo logs de los hábitos del usuario actual
        return HabitLog.objects.filter(habit__user=self.request.user)
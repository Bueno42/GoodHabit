from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Habit, HabitLog
from .serializers import HabitSerializer, HabitLogSerializer

class HabitViewSet(viewsets.ModelViewSet):
    queryset = Habit.objects.all()
    serializer_class = HabitSerializer

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
    queryset = HabitLog.objects.all()
    serializer_class = HabitLogSerializer
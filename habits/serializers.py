from rest_framework import serializers
from .models import Habit, HabitLog

class HabitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitLog
        fields = ['id', 'habit', 'date', 'completed', 'actual_value', 'notes']


class HabitSerializer(serializers.ModelSerializer):
    # Traemos los logs anidados (últimos registros) para lectura
    logs = HabitLogSerializer(many=True, read_only=True)

    class Meta:
        model = Habit
        fields = [
            'id',
            'user',
            'name',
            'description',
            'frequency',
            'goal_type',
            'target_value',
            'unit',
            'is_active',
            'created_at',
            'updated_at',
            'logs'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
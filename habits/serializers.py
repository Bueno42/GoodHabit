from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Habit, HabitLog, HabitPadrino

class HabitPadrinoSerializer(serializers.ModelSerializer):
    padrino_username = serializers.CharField(source='padrino.username', read_only=True)

    class Meta:
        model = HabitPadrino
        fields = ['id', 'padrino', 'padrino_username', 'estado_invitacion', 'fecha_asignacion']
        read_only_fields = ['id', 'estado_invitacion', 'fecha_asignacion']


class HabitLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = HabitLog
        fields = ['id', 'habit', 'date', 'completed', 'actual_value', 'notes']


class HabitSerializer(serializers.ModelSerializer):
    # Mostramos los padrinos asociados al hábito
    padrino_assignments = HabitPadrinoSerializer(many=True, read_only=True)

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
            'padrino_assignments',
            'is_active',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
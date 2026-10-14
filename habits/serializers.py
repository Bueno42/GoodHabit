from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *

class HabitPadrinoSerializer(serializers.ModelSerializer):
    padrino_username = serializers.CharField(source='padrino.username', read_only=True)

    class Meta:
        model = HabitPadrino
        fields = ['id', 'padrino', 'padrino_username', 'estado_invitacion', 'fecha_asignacion']
        read_only_fields = ['id', 'estado_invitacion', 'fecha_asignacion']

    #Tambien se ejecuta en models.py pero es buena practica validarlo aca tambien
    def validate(self, data):
        habit = data.get('habit')
        padrino = data.get('padrino')

        if habit and padrino:
            #Validamos autorreferencia
            if habit.user == padrino:
                raise serializers.ValidationError("Un usuario no puede ser padrino de su propio hábito.")
            #Validamos cupo excluyendo solicitudes rechazadas
            padrinos_activos = HabitPadrino.objects.filter(habit=habit).exclude(
                estado_invitacion = HabitPadrino.EstadoInvitacion.RECHAZADO
            ).count()

            if padrinos_activos >= 2:
                raise serializers.ValidationError("Este habito ya alcanzo el limite maximo de 2 padrinos. ")

        return data


class HabitLogSerializer(serializers.ModelSerializer):
    revisado_por_username = serializers.CharField(source='revisado_por.username', read_only=True)
    evidencia_url = serializers.CharField(source='evidencia.s3_file_url', read_only=True)

    class Meta:
        model = HabitLog
        fields = [
            'id', 'habit', 'date', 'estado', 'actual_value', 
            'notes', 'revisado_por', 'revisado_por_username', 
            'fecha_envio', 'fecha_revision', 'motivo_rechazo', 'evidencia_url'
        ]
        read_only_fields = ['id', 'estado', 'revisado_por', 'fecha_envio', 'fecha_revision']


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

class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['id', 'habit', 'usuario', 's3_file_url', 'descripcion', 'estado', 'fecha_creacion']
        read_only_fields = ['id', 'usuario', 'estado', 'fecha_creacion']

class PresignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=50)


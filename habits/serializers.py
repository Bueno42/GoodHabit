from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth.models import User
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']

class HabitPadrinoSerializer(serializers.ModelSerializer):
    padrino_username = serializers.CharField(source='padrino.username', read_only=True)
    habito_nombre = serializers.ReadOnlyField(source='habit.name')

    class Meta:
        model = HabitPadrino
        fields = ['id', 'habit', 'habito_nombre', 'padrino', 'padrino_username', 'estado_invitacion', 'fecha_asignacion']
        read_only_fields = ['id', 'fecha_asignacion']

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


from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone  # NO TE OLVIDES DE IMPORTAR ESTO
from .models import *

# ... (Tus otros serializadores quedan igual) ...

class HabitSerializer(serializers.ModelSerializer):
    # Mostramos los padrinos asociados al hábito
    padrino_assignments = HabitPadrinoSerializer(many=True, read_only=True)
    
    # NUEVO: Campo calculado para saber si hoy ya se cumplió/mandó a revisión
    estado_hoy = serializers.SerializerMethodField()

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
            'updated_at',
            'estado_hoy'  # NO TE OLVIDES DE AGREGARLO ACÁ
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_estado_hoy(self, obj):
        hoy = timezone.now().date()
        log = obj.logs.filter(date=hoy).first()
        
        if log:
            return log.estado
        return None

class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['id', 'habit_log', 'usuario', 's3_file_url', 'descripcion', 'fecha_creacion']
        read_only_fields = ['id', 'usuario', 'fecha_creacion']

class PresignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=50)


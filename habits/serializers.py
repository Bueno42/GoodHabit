from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import *

User = get_user_model()

class InvitarPadrinoSerializer(serializers.Serializer):
    padrino_email = serializers.EmailField()

    def validate_padrino_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No existe ningún usuario registrado con este correo.")
        return user

class RespuestaPadrinoSerializer(serializers.Serializer):
    aceptar = serializers.BooleanField()

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
        validators = []

    #Tambien se ejecuta en models.py pero es buena practica validarlo aca tambien
    def validate(self, data):
        habit = data.get('habit', getattr(self.instance, 'habit', None))
        padrino = data.get('padrino', getattr(self.instance, 'padrino', None))

        if habit and padrino:
            invitaciones_existentes = HabitPadrino.objects.filter(
                habit=habit,
                padrino=padrino,
            )
            if self.instance:
                invitaciones_existentes = invitaciones_existentes.exclude(pk=self.instance.pk)

            invitacion_existente = invitaciones_existentes.first()
            puede_reenviar_invitacion_rechazada = (
                self.instance is None
                and invitacion_existente is not None
                and invitacion_existente.estado_invitacion == HabitPadrino.EstadoInvitacion.RECHAZADO
            )
            if invitacion_existente and not puede_reenviar_invitacion_rechazada:
                raise serializers.ValidationError({
                    'padrino': 'Este usuario ya tiene una invitación activa para este hábito.'
                })

            #Validamos autorreferencia
            if habit.user == padrino:
                raise serializers.ValidationError("Un usuario no puede ser padrino de su propio hábito.")
            #Validamos cupo excluyendo solicitudes rechazadas
            padrinos_activos = HabitPadrino.objects.filter(
                habit=habit,
                estado_invitacion__in=[
                    HabitPadrino.EstadoInvitacion.PENDIENTE,
                    HabitPadrino.EstadoInvitacion.ACEPTADO,
                ],
            )
            if self.instance:
                padrinos_activos = padrinos_activos.exclude(pk=self.instance.pk)

            if padrinos_activos.count() >= 2:
                raise serializers.ValidationError("Este habito ya alcanzo el limite maximo de 2 padrinos. ")

        return data

    def create(self, validated_data):
        habit = validated_data['habit']
        padrino = validated_data['padrino']
        invitacion_existente = HabitPadrino.objects.filter(
            habit=habit,
            padrino=padrino,
            estado_invitacion=HabitPadrino.EstadoInvitacion.RECHAZADO,
        ).first()

        if invitacion_existente:
            invitacion_existente.estado_invitacion = HabitPadrino.EstadoInvitacion.PENDIENTE
            invitacion_existente.fecha_asignacion = timezone.now()
            invitacion_existente.save(update_fields=['estado_invitacion', 'fecha_asignacion'])
            return invitacion_existente

        return super().create(validated_data)

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
    file_type = serializers.ChoiceField(choices=('image/jpeg', 'image/png', 'video/mp4'))

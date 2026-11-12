from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Habit, HabitLog, HabitPadrino, Evidencia
from .services import generar_presigned_url_lectura, calcular_racha_actual

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
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        read_only_fields = ['id']

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario registrado con este correo electrónico.")
        return value.lower()

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )

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

            request = self.context.get('request')
            if self.instance is None and request and request.user.is_authenticated and habit.user != request.user:
                raise serializers.ValidationError({
                    'habit': 'No podés asignar padrinos a un hábito que no te pertenece.'
                })
            
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
    habit_name = serializers.ReadOnlyField(source='habit.name')
    ahijado_username = serializers.ReadOnlyField(source='habit.user.username')
    evidencia_url = serializers.SerializerMethodField()

    class Meta:
        model = HabitLog
        fields = [
            'id', 'habit', 'habit_name', 'ahijado_username', 'date', 'estado', 
            'actual_value', 'notes', 'revisado_por', 'revisado_por_username', 
            'fecha_envio', 'fecha_revision', 'motivo_rechazo', 'evidencia_url'
        ]
        read_only_fields = ['id', 'estado', 'revisado_por', 'fecha_envio', 'fecha_revision']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_evidencia_url(self, obj):
        if hasattr(obj, 'evidencia') and obj.evidencia and obj.evidencia.s3_file_url:
            return generar_presigned_url_lectura(obj.evidencia.s3_file_url)
        return None


from rest_framework import serializers
from django.contrib.auth.models import User
from .models import *



class HabitSerializer(serializers.ModelSerializer):
    padrino_assignments = HabitPadrinoSerializer(many=True, read_only=True)
    estado_hoy = serializers.SerializerMethodField()
    motivo_rechazo_hoy = serializers.SerializerMethodField()
    racha_actual = serializers.SerializerMethodField()
    tasa_cumplimiento = serializers.SerializerMethodField()

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
            'estado_hoy',
            'motivo_rechazo_hoy',
            'racha_actual',
            'tasa_cumplimiento'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


    def get_racha_actual(self, obj):
        return calcular_racha_actual(obj)

    def get_tasa_cumplimiento(self, obj):
        total = obj.logs.count()
        if total == 0:
            return 0
        aprobados = obj.logs.filter(estado__in=['APROBADO', 'APROBADO_TIMEOUT']).count()
        return round((aprobados/total) * 100, 1)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_estado_hoy(self, obj):
        hoy = timezone.localdate()
        log = obj.logs.filter(date=hoy).first()
        return log.estado if log else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_motivo_rechazo_hoy(self, obj):
        hoy = timezone.localdate()
        log = obj.logs.filter(date=hoy).first()
        if log and log.estado == HabitLog.Estado.RECHAZADO:
            return log.motivo_rechazo
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_racha_actual(self, obj):
        logs_aprobados = set(
            obj.logs.filter(
                estado__in=[HabitLog.Estado.APROBADO, HabitLog.Estado.TIMEOUT_APROBADO]
            ).values_list('date', flat=True)
        )
        if not logs_aprobados:
            return 0

        def es_dia_programado(fecha):
            if obj.frequency == 'WEEKDAYS':
                return fecha.weekday() < 5  # Lunes (0) a Viernes (4)
            if obj.frequency == 'WEEKENDS':
                return fecha.weekday() >= 5  # Sábado (5) y Domingo (6)
            return True  # DAILY / CUSTOM

        hoy = timezone.localdate()
        dia_cursor = hoy

        # Si hoy aún no se cumplió (o no tocaba), retrocedemos hasta el último día programado esperado
        if dia_cursor not in logs_aprobados:
            dia_cursor -= timezone.timedelta(days=1)
            while not es_dia_programado(dia_cursor):
                dia_cursor -= timezone.timedelta(days=1)

        racha = 0
        while True:
            if not es_dia_programado(dia_cursor):
                dia_cursor -= timezone.timedelta(days=1)
                continue
            if dia_cursor in logs_aprobados:
                racha += 1
                dia_cursor -= timezone.timedelta(days=1)
            else:
                break

        return racha

class EvidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidencia
        fields = ['id', 'habit_log', 'usuario', 's3_file_url', 'descripcion', 'fecha_creacion']
        read_only_fields = ['id', 'usuario', 'fecha_creacion']
        extra_kwargs = {
            'habit_log': {'validators': []}
        }

class PresignedURLSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.ChoiceField(choices=('image/jpeg', 'image/png', 'video/mp4'))

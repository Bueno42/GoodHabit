from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Habit, HabitLog, HabitPadrino, Evidencia
from .services import (
    generar_presigned_url_lectura,
    calcular_racha_actual,
    aplicar_timeout_revisiones,
)

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
        fields = [
            'id',
            'habit',
            'habito_nombre',
            'padrino',
            'padrino_username',
            'estado_invitacion',
            'fecha_asignacion',
        ]
        read_only_fields = ['id', 'fecha_asignacion']
        validators = []

    def validate(self, data):
        habit = data.get('habit', getattr(self.instance, 'habit', None))
        padrino = data.get('padrino', getattr(self.instance, 'padrino', None))

        if habit and padrino:
            request = self.context.get('request')
            if self.instance is None and request and request.user.is_authenticated and habit.user != request.user:
                raise serializers.ValidationError({
                    'habit': 'No podés asignar padrinos a un hábito que no te pertenece.'
                })

            if not habit.is_premium:
                raise serializers.ValidationError({
                    'habit': 'Solo los hábitos en Modo Desafío Premium permiten asignar padrinos.'
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

            if habit.user == padrino:
                raise serializers.ValidationError("Un usuario no puede ser padrino de su propio hábito.")

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
                raise serializers.ValidationError("Este hábito ya alcanzó el límite máximo de 2 padrinos.")

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
            'id',
            'habit',
            'habit_name',
            'ahijado_username',
            'date',
            'estado',
            'actual_value',
            'notes',
            'revisado_por',
            'revisado_por_username',
            'fecha_envio',
            'fecha_revision',
            'motivo_rechazo',
            'evidencia_url',
        ]
        read_only_fields = ['id', 'estado', 'revisado_por', 'fecha_envio', 'fecha_revision']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_evidencia_url(self, obj):
        if hasattr(obj, 'evidencia') and obj.evidencia and obj.evidencia.s3_file_url:
            return generar_presigned_url_lectura(obj.evidencia.s3_file_url)
        return None


class HabitSerializer(serializers.ModelSerializer):
    padrino_assignments = HabitPadrinoSerializer(many=True, read_only=True)
    estado_hoy = serializers.SerializerMethodField()
    motivo_rechazo_hoy = serializers.SerializerMethodField()
    racha_actual = serializers.SerializerMethodField()
    tasa_cumplimiento = serializers.SerializerMethodField()
    logs_aprobados_count = serializers.SerializerMethodField()
    codigo_recompensa = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            'id',
            'user',
            'name',
            'description',
            'category',
            'duration_days',
            'frequency',
            'goal_type',
            'target_value',
            'unit',
            'is_premium',
            'padrino_assignments',
            'is_active',
            'created_at',
            'updated_at',
            'estado_hoy',
            'motivo_rechazo_hoy',
            'racha_actual',
            'tasa_cumplimiento',
            'logs_aprobados_count',
            'codigo_recompensa',
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def _logs_validos_qs(self, obj):
        aplicar_timeout_revisiones(obj)
        if obj.is_premium:
            return obj.logs.filter(evidencia__isnull=False)
        return obj.logs.all()

    @extend_schema_field(serializers.IntegerField())
    def get_logs_aprobados_count(self, obj):
        return self._logs_validos_qs(obj).filter(
            estado__in=[HabitLog.Estado.APROBADO, HabitLog.Estado.TIMEOUT_APROBADO]
        ).count()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_codigo_recompensa(self, obj):
        """
        Sección 4.2 - Premios Digitales: Exclusivo del Modo Desafío Premium.
        Al completar el 100% de los registros requeridos durante el plazo del desafío,
        el sistema libera un código de canje único (Gift Card).
        """
        if not obj.is_premium:
            return None
        aprobados = self.get_logs_aprobados_count(obj)
        plazo = obj.duration_days or 21
        if aprobados >= plazo:
            return f"GH-GIFT-{obj.user_id:02d}{obj.id:03d}-{plazo}D"
        return None

    @extend_schema_field(serializers.FloatField())
    def get_tasa_cumplimiento(self, obj):
        qs = self._logs_validos_qs(obj)
        total = qs.count()
        if total == 0:
            return 0.0
        aprobados = qs.filter(
            estado__in=[HabitLog.Estado.APROBADO, HabitLog.Estado.TIMEOUT_APROBADO]
        ).count()
        return round((aprobados / total) * 100, 1)

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_estado_hoy(self, obj):
        hoy = timezone.localdate()
        log_hoy = self._logs_validos_qs(obj).filter(date=hoy).order_by('-id').first()
        return log_hoy.estado if log_hoy else None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_motivo_rechazo_hoy(self, obj):
        hoy = timezone.localdate()
        log_hoy = self._logs_validos_qs(obj).filter(date=hoy).order_by('-id').first()
        if log_hoy and log_hoy.estado == HabitLog.Estado.RECHAZADO:
            return log_hoy.motivo_rechazo
        return None

    @extend_schema_field(serializers.IntegerField())
    def get_racha_actual(self, obj):
        return calcular_racha_actual(obj)


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
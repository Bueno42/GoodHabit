from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone


class HabitPadrino(models.Model):
    class EstadoInvitacion(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ACEPTADO = 'ACEPTADO', 'Aceptado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'

    habit = models.ForeignKey(
        'Habit',
        on_delete=models.CASCADE,
        related_name='padrino_assignments'
    )
    padrino = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='padrinazgos'
    )
    estado_invitacion = models.CharField(
        max_length=20,
        choices=EstadoInvitacion.choices,
        default=EstadoInvitacion.PENDIENTE
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Padrino de Hábito'
        verbose_name_plural = 'Padrinos de Hábitos'
        unique_together = ('habit', 'padrino')

    def clean(self):
        super().clean()

        # Regla 0: Solo hábitos en Modo Desafío Premium admiten padrinos
        if self.habit_id and not self.habit.is_premium:
            raise ValidationError("Solo los hábitos en Modo Desafío Premium permiten asignar padrinos.")

        # Regla 1: Un usuario no puede auto-asignarse como su propio padrino
        if self.habit_id and self.habit.user.id == self.padrino_id:
            raise ValidationError("Un usuario no puede ser padrino de su propio hábito.")

        # Regla 2: Máximo 2 padrinos por hábito (Sección 4.7)
        if self.habit_id:
            padrinos_actuales = HabitPadrino.objects.filter(
                habit=self.habit,
                estado_invitacion__in=[
                    self.EstadoInvitacion.PENDIENTE,
                    self.EstadoInvitacion.ACEPTADO,
                ]
            ).exclude(id=self.id).count()

            if padrinos_actuales >= 2:
                raise ValidationError("Este hábito ya alcanzó el límite máximo de 2 padrinos.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.padrino.username} -> {self.habit.name} ({self.estado_invitacion})"


class Habit(models.Model):
    class FrequencyType(models.TextChoices):
        DAILY = 'DAILY', 'Diario'
        WEEKDAYS = 'WEEKDAYS', 'Días hábiles'
        WEEKENDS = 'WEEKENDS', 'Fines de semana'
        CUSTOM = 'CUSTOM', 'Personalizado'

    class GoalType(models.TextChoices):
        BOOLEAN = 'BOOL', 'Completado / No completado'
        NUMERIC = 'NUM', 'Meta numérica'

    class CategoryType(models.TextChoices):
        SALUD = 'SALUD', 'Salud y Fitness'
        ESTUDIO = 'ESTUDIO', 'Estudio y Lectura'
        PRODUCTIVIDAD = 'PRODUCTIVIDAD', 'Productividad'
        MINDFULNESS = 'MINDFULNESS', 'Mindfulness y Bienestar'
        FINANZAS = 'FINANZAS', 'Finanzas Personales'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    name = models.CharField(max_length=150, verbose_name="Nombre del hábito")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")

    # Sección 4.1: Categoría (Comunidad temática) y Duración del Desafío
    category = models.CharField(
        max_length=25,
        choices=CategoryType.choices,
        default=CategoryType.SALUD,
        verbose_name="Categoría / Comunidad"
    )
    duration_days = models.PositiveIntegerField(
        default=21,
        verbose_name="Duración del Desafío (días)",
        help_text="Plazo definido del desafío (ej. 21, 30, 60 o 90 días)"
    )

    frequency = models.CharField(
        max_length=20,
        choices=FrequencyType.choices,
        default=FrequencyType.DAILY
    )
    goal_type = models.CharField(
        max_length=10,
        choices=GoalType.choices,
        default=GoalType.BOOLEAN
    )
    target_value = models.PositiveIntegerField(
        default=1,
        help_text="Meta diaria (ej: 1 si es booleano, o cantidad de páginas, minutos, etc.)"
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Ej: páginas, litros, minutos"
    )
    is_premium = models.BooleanField(
        default=False,
        verbose_name="Modo Desafío Premium",
        help_text="Si es True, habilita hasta 2 padrinos y exige evidencia en AWS S3."
    )
    padrinos = models.ManyToManyField(
        User,
        through='HabitPadrino',
        related_name='habitos_supervisados',
        blank=True
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class HabitLog(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_REVISION = 'EN_REVISION', 'En revisión'
        APROBADO = 'APROBADO', 'Aprobado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'
        TIMEOUT_APROBADO = 'TIMEOUT_APROBADO', 'Aprobado por timeout'

    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField(default=timezone.localdate, verbose_name="Fecha del registro")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    actual_value = models.PositiveIntegerField(default=0)
    notes = models.CharField(max_length=255, blank=True, null=True)

    revisado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='revisiones_realizadas'
    )
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    motivo_rechazo = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.habit.name} - {self.date}: {self.estado}"


class Evidencia(models.Model):
    habit_log = models.OneToOneField(
        HabitLog,
        on_delete=models.CASCADE,
        related_name='evidencia',
        null=True,
        blank=True
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    s3_file_url = models.URLField(max_length=500)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidencia {self.id} - Usuario: {self.usuario.username}"
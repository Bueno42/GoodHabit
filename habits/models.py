from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

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
        User, 
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
        # Evita asignar al mismo padrino dos veces al mismo hábito
        unique_together = ('habit', 'padrino')
        verbose_name = 'Padrino de Hábito'
        verbose_name_plural = 'Padrinos de Hábitos'

    def clean(self):
        super().clean()

        # Regla 1: Un usuario no puede auto-asignarse como su propio padrino
        if self.habit_id and self.padrino_id and self.habit.user_id == self.padrino_id:
            raise ValidationError("Un usuario no puede ser padrino de su propio hábito.")

        # Regla 2: Máximo 2 padrinos por hábito
        if self.habit_id and not self.pk:
            total_actual = HabitPadrino.objects.filter(habit=self.habit).count()
            if total_actual >= 2:
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

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='habits')
    name = models.CharField(max_length=150, verbose_name="Nombre del hábito")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    
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
    habit = models.ForeignKey(Habit, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField(verbose_name="Fecha del registro")
    completed = models.BooleanField(default=False)
    actual_value = models.PositiveIntegerField(default=0, help_text="Valor alcanzado en el día")
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ('habit', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.habit.name} - {self.date}: {'Cumplido' if self.completed else 'Pendiente'}"
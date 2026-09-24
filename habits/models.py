from django.db import models
from django.contrib.auth.models import User

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
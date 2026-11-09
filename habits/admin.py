from django.contrib import admin
from .models import Habit, HabitLog, HabitPadrino, Evidencia

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'frequency', 'goal_type', 'target_value', 'is_active', 'created_at')
    list_filter = ('frequency', 'goal_type', 'is_active')
    search_fields = ('name', 'user__username')

@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'habit', 'date', 'estado', 'actual_value', 'revisado_por', 'fecha_revision')
    list_filter = ('estado', 'date')
    search_fields = ('habit__name', 'notes', 'revisado_por__username')

@admin.register(HabitPadrino)
class HabitPadrinoAdmin(admin.ModelAdmin):
    list_display = ('id', 'habit', 'padrino', 'estado_invitacion', 'fecha_asignacion')
    list_filter = ('estado_invitacion',)

@admin.register(Evidencia)
class EvidenciaAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'habit_log', 'fecha_creacion')
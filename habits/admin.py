from django.contrib import admin
from .models import Habit, HabitLog

@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'frequency', 'goal_type', 'target_value', 'is_active', 'created_at')
    list_filter = ('frequency', 'goal_type', 'is_active')
    search_fields = ('name', 'user__username')

@admin.register(HabitLog)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'habit', 'date', 'completed', 'actual_value')
    list_filter = ('completed', 'date')
    search_fields = ('habit__name', 'notes')
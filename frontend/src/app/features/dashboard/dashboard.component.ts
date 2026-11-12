import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { V1Service } from '../../api/api/v1.service';
import { Habit } from '../../api/model/habit';
import { FrequencyEnum } from '../../api/model/frequencyEnum';
import { GoalTypeEnum } from '../../api/model/goalTypeEnum';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  habitos: Habit[] = [];
  cargando = true;
  error = '';
  mensajeExito = '';
  registrandoHabitId: number | null = null;

  // Estado Cuenta Premium y Checkout Simulado de Mercado Pago
  esCuentaPremium = false;
  mostrarModalMercadoPago = false;
  procesandoPago = false;

  // Estado ABM #1: Modificación y Baja de Hábito
  habitoEditandoId: number | null = null;
  guardandoEdicion = false;
  eliminandoHabitId: number | null = null;
  formEdicion: {
    name: string;
    description: string;
    frequency: FrequencyEnum;
    goal_type: GoalTypeEnum;
    target_value: number;
    unit: string;
    is_premium: boolean;
  } = {
    name: '',
    description: '',
    frequency: 'DAILY' as FrequencyEnum,
    goal_type: 'BOOL' as GoalTypeEnum,
    target_value: 1,
    unit: '',
    is_premium: false
  };

  private apiService = inject(V1Service);
  private router = inject(Router);

  ngOnInit() {
    this.esCuentaPremium = localStorage.getItem(this.obtenerClaveStoragePremium()) === 'true';
    this.cargarHabitos();
  }

  private obtenerClaveStoragePremium(): string {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload?.user_id) {
          return `goodhabit_premium_user_${payload.user_id}`;
        }
      } catch {
        // Fallback
      }
    }
    return 'goodhabit_premium_default';
  }

  abrirModalMercadoPago() {
    this.mostrarModalMercadoPago = true;
  }

  cerrarModalMercadoPago() {
    if (this.procesandoPago) return;
    this.mostrarModalMercadoPago = false;
  }

  confirmarPagoMercadoPago() {
    if (this.procesandoPago) return;
    this.procesandoPago = true;

    setTimeout(() => {
      localStorage.setItem(this.obtenerClaveStoragePremium(), 'true');
      this.esCuentaPremium = true;
      if (this.habitoEditandoId !== null) {
        this.formEdicion.is_premium = true;
      }
      this.procesandoPago = false;
      this.mostrarModalMercadoPago = false;
      this.mensajeExito = '⭐ ¡Pago procesado con éxito! Ya podés crear y configurar hábitos en Modo Desafío Premium.';
    }, 1400);
  }

  cargarHabitos() {
    this.cargando = true;
    this.apiService.v1HabitsList().subscribe({
      next: (data) => {
        this.habitos = data;
        if (data.some(h => h.is_premium)) {
          this.esCuentaPremium = true;
          localStorage.setItem(this.obtenerClaveStoragePremium(), 'true');
        }
        this.cargando = false;
      },
      error: (err) => {
        console.error(err);
        this.error = 'No se pudieron cargar los hábitos. Verificá tu sesión.';
        this.cargando = false;
      }
    });
  }

  // Resumen Diario en el Dashboard
  get habitosCompletadosHoy(): number {
    return this.habitos.filter(
      h => h.estado_hoy === 'APROBADO' || h.estado_hoy === 'TIMEOUT_APROBADO'
    ).length;
  }

  get habitosEnRevisionHoy(): number {
    return this.habitos.filter(h => h.estado_hoy === 'EN_REVISION').length;
  }

  get porcentajeCumplimientoHoy(): number {
    if (!this.habitos.length) return 0;
    return Math.round((this.habitosCompletadosHoy / this.habitos.length) * 100);
  }

  traducirFrecuencia(freq?: string): string {
    const mapa: Record<string, string> = {
      DAILY: 'Diario',
      WEEKDAYS: 'Días hábiles (Lun a Vie)',
      WEEKENDS: 'Fines de semana',
      CUSTOM: 'Personalizado'
    };
    return freq ? (mapa[freq] || freq) : 'Diario';
  }

  formatearMeta(habito: Habit): string {
    if (habito.goal_type === 'BOOL') {
      return 'Completar en el día';
    }
    const unidad = habito.unit ? ` ${habito.unit}` : '';
    return `${habito.target_value ?? 1}${unidad}`;
  }

  iniciarEdicion(habito: Habit) {
    this.error = '';
    this.mensajeExito = '';
    this.habitoEditandoId = habito.id!;
    this.formEdicion = {
      name: habito.name || '',
      description: habito.description || '',
      frequency: (habito.frequency as FrequencyEnum) || ('DAILY' as FrequencyEnum),
      goal_type: (habito.goal_type as GoalTypeEnum) || ('BOOL' as GoalTypeEnum),
      target_value: habito.target_value ?? 1,
      unit: habito.unit || '',
      is_premium: !!habito.is_premium
    };
  }

  onCambioPremiumEdicion(nuevoValor: boolean) {
    if (nuevoValor && !this.esCuentaPremium) {
      this.formEdicion.is_premium = false;
      this.abrirModalMercadoPago();
      return;
    }
    this.formEdicion.is_premium = nuevoValor;
  }

  cancelarEdicion() {
    this.habitoEditandoId = null;
  }

  guardarEdicion(habitId: number) {
    if (!this.formEdicion.name.trim()) {
      this.error = 'El nombre del hábito no puede estar vacío.';
      return;
    }

    this.guardandoEdicion = true;
    this.error = '';
    this.mensajeExito = '';

    const payload = {
      name: this.formEdicion.name.trim(),
      description: this.formEdicion.description?.trim() || '',
      frequency: this.formEdicion.frequency,
      goal_type: this.formEdicion.goal_type,
      target_value: this.formEdicion.goal_type === 'BOOL' ? 1 : this.formEdicion.target_value,
      unit: this.formEdicion.goal_type === 'BOOL' ? '' : this.formEdicion.unit.trim(),
      is_premium: this.formEdicion.is_premium
    };

    this.apiService.v1HabitsPartialUpdate(habitId, payload).subscribe({
      next: (habitoActualizado) => {
        this.habitos = this.habitos.map(h => h.id === habitId ? habitoActualizado : h);
        this.habitoEditandoId = null;
        this.guardandoEdicion = false;
        this.mensajeExito = `Hábito "${habitoActualizado.name}" actualizado correctamente.`;
      },
      error: (err) => {
        console.error('Error al actualizar hábito', err);
        this.error = this.mensajeErrorRegistro(err);
        this.guardandoEdicion = false;
      }
    });
  }

  eliminarHabito(habito: Habit) {
    if (!habito.id || this.eliminandoHabitId !== null) return;

    const confirmar = window.confirm(`¿Estás seguro de que querés eliminar el hábito "${habito.name}"? Esta acción borrará también su historial.`);
    if (!confirmar) return;

    this.error = '';
    this.mensajeExito = '';
    this.eliminandoHabitId = habito.id;

    this.apiService.v1HabitsDestroy(habito.id).subscribe({
      next: () => {
        this.habitos = this.habitos.filter(h => h.id !== habito.id);
        this.eliminandoHabitId = null;
        this.mensajeExito = `El hábito "${habito.name}" fue eliminado.`;
      },
      error: (err) => {
        console.error('Error al eliminar hábito', err);
        this.error = 'No se pudo eliminar el hábito. Intentá nuevamente.';
        this.eliminandoHabitId = null;
      }
    });
  }

  registrarEjecucion(habito: Habit) {
    if (!habito.id || this.registrandoHabitId !== null) {
      return;
    }

    this.error = '';
    this.mensajeExito = '';
    this.registrandoHabitId = habito.id;

    const payload = {
      habit: habito.id,
      actual_value: habito.goal_type === 'NUM' ? (habito.target_value ?? 1) : 1
    };

    this.apiService.v1LogsCreate(payload).subscribe({
      next: (nuevoLog: any) => {
        this.registrandoHabitId = null;

        if (habito.is_premium) {
          this.router.navigate(['/evidencia', nuevoLog.id]);
        } else {
          this.mensajeExito = `✅ ¡Hábito "${habito.name}" registrado como completado hoy (Autodeclaración)!`;
          this.cargarHabitos();
        }
      },
      error: (err) => {
        console.error('Error al generar el registro en el backend', err);
        this.registrandoHabitId = null;
        this.error = this.mensajeErrorRegistro(err);
      }
    });
  }

  private mensajeErrorRegistro(err: HttpErrorResponse): string {
    if (err.status === 401) {
      return 'Tu sesión venció. Iniciá sesión nuevamente.';
    }
    if (err.status === 0) {
      return 'No se pudo conectar con el servidor. Verificá que el backend esté iniciado.';
    }

    const body = err.error;
    if (typeof body === 'string' && body.trim()) {
      return body;
    }
    if (typeof body?.detail === 'string') {
      return body.detail;
    }
    if (body && typeof body === 'object') {
      const messages = Object.values(body)
        .flatMap((value) => Array.isArray(value) ? value : [value])
        .filter((value): value is string => typeof value === 'string');
      if (messages.length > 0) {
        return messages.join(' ');
      }
    }

    return `Ocurrió un error al procesar la solicitud (HTTP ${err.status}).`;
  }
}
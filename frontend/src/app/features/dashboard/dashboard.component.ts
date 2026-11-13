import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { HttpErrorResponse } from '@angular/common/http';
import { V1Service } from '../../api/api/v1.service';
import { Habit } from '../../api/model/habit';
import { FrequencyEnum } from '../../api/model/frequencyEnum';
import { GoalTypeEnum } from '../../api/model/goalTypeEnum';

export interface InsigniaUsuario {
  icono: string;
  nombre: string;
  descripcion: string;
  desbloqueada: boolean;
}

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

  // Filtro de Comunidades Temáticas (Sección 4.1 y 4.3) y Privacidad
  comunidadSeleccionada = 'TODAS';
  nivelPrivacidad: 'CIRCULO' | 'COMUNIDAD' | 'PRIVADO' = 'CIRCULO';
  recordatorioHora = '20:00';
  notificacionesActivas = false;

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
    category: string;
    duration_days: number;
    frequency: FrequencyEnum;
    goal_type: GoalTypeEnum;
    target_value: number;
    unit: string;
    is_premium: boolean;
  } = {
    name: '',
    description: '',
    category: 'SALUD',
    duration_days: 21,
    frequency: 'DAILY' as FrequencyEnum,
    goal_type: 'BOOL' as GoalTypeEnum,
    target_value: 1,
    unit: '',
    is_premium: false
  };

  private apiService = inject(V1Service);
  private router = inject(Router);

  ngOnInit() {
    this.esCuentaPremium = localStorage.getItem(this.obtenerClaveStorage('premium')) === 'true';
    const privGuardada = localStorage.getItem(this.obtenerClaveStorage('privacidad')) as any;
    if (privGuardada) {
      this.nivelPrivacidad = privGuardada;
    }
    this.notificacionesActivas = localStorage.getItem(this.obtenerClaveStorage('notif')) === 'true';
    this.cargarHabitos();
  }

  private obtenerClaveStorage(sufijo: string): string {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload?.user_id) {
          return `goodhabit_${sufijo}_user_${payload.user_id}`;
        }
      } catch {
        // Fallback
      }
    }
    return `goodhabit_${sufijo}_default`;
  }

  guardarPrivacidad() {
    localStorage.setItem(this.obtenerClaveStorage('privacidad'), this.nivelPrivacidad);
    this.mensajeExito = '🔒 Configuración de privacidad y círculo de confianza actualizada.';
  }

  activarNotificacionesPush() {
    if ('Notification' in window) {
      Notification.requestPermission().then(permiso => {
        this.notificacionesActivas = true;
        localStorage.setItem(this.obtenerClaveStorage('notif'), 'true');
        if (permiso === 'granted') {
          new Notification('GoodHabit • Recordatorio Configurado', {
            body: `Te avisaremos a las ${this.recordatorioHora} hs si tenés hábitos pendientes antes del corte de la 01:00 AM.`
          });
        }
        this.mensajeExito = `🔔 Recordatorios Push activados para las ${this.recordatorioHora} hs.`;
      });
    } else {
      this.notificacionesActivas = true;
      localStorage.setItem(this.obtenerClaveStorage('notif'), 'true');
      this.mensajeExito = `🔔 Recordatorios diarios activados para las ${this.recordatorioHora} hs.`;
    }
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
      localStorage.setItem(this.obtenerClaveStorage('premium'), 'true');
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
          localStorage.setItem(this.obtenerClaveStorage('premium'), 'true');
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

  // =========================================================================
  // SECCIÓN 4.2 y 4.4: GAMIFICACIÓN (XP, FÓRMULA 100 * N^1.5, INSIGNIAS, GIFT CARD)
  // =========================================================================

  get totalRegistrosAprobados(): number {
    return this.habitos.reduce((acc, h: any) => acc + (h.logs_aprobados_count || 0), 0);
  }

  get rachaMaximaUsuario(): number {
    if (!this.habitos.length) return 0;
    return Math.max(...this.habitos.map(h => h.racha_actual || 0));
  }

  get bonosSemanalesGanados(): number {
    // Bono de +150 XP por cada semana completa de constancia acumulada
    return Math.floor(this.totalRegistrosAprobados / 7);
  }

  get xpTotalUsuario(): number {
    // +50 XP por cada registro aprobado + 150 XP por bono semanal
    return (this.totalRegistrosAprobados * 50) + (this.bonosSemanalesGanados * 150);
  }

  get xpGanadoHoy(): number {
    const baseHoy = this.habitosCompletadosHoy * 50;
    const bonoJornadaCompleta = (this.habitos.length > 0 && this.habitosCompletadosHoy === this.habitos.length) ? 150 : 0;
    return baseHoy + bonoJornadaCompleta;
  }

  xpRequeridaParaNivel(nivel: number): number {
    // Fórmula polinómica exacta de la Sección 4.2: XP_Necesaria = 100 * (N ^ 1.5)
    return Math.round(100 * Math.pow(nivel, 1.5));
  }

  get nivelActualUsuario(): number {
    let nivel = 1;
    while (this.xpTotalUsuario >= this.xpRequeridaParaNivel(nivel)) {
      nivel++;
    }
    return nivel;
  }

  get xpMetaNivelActual(): number {
    return this.xpRequeridaParaNivel(this.nivelActualUsuario);
  }

  get porcentajeProgresoNivel(): number {
    const xpPiso = this.nivelActualUsuario === 1 ? 0 : this.xpRequeridaParaNivel(this.nivelActualUsuario - 1);
    const xpTecho = this.xpMetaNivelActual;
    const rango = Math.max(1, xpTecho - xpPiso);
    return Math.min(100, Math.max(0, Math.round(((this.xpTotalUsuario - xpPiso) / rango) * 100)));
  }

  get insigniasUsuario(): InsigniaUsuario[] {
    const tienePadrinoActivo = this.habitos.some(h => (h.padrino_assignments || []).length > 0);
    const tieneDesafioCumplido = this.habitos.some((h: any) => !!h.codigo_recompensa);

    return [
      {
        icono: '🌱',
        nombre: 'Primer Paso',
        descripcion: 'Primer registro de hábito completado (+50 XP)',
        desbloqueada: this.totalRegistrosAprobados >= 1
      },
      {
        icono: '🥉',
        nombre: 'Constancia de Bronce',
        descripcion: 'Alcanzar una racha de 3 o más días consecutivos',
        desbloqueada: this.rachaMaximaUsuario >= 3
      },
      {
        icono: '🥈',
        nombre: 'Constancia de Plata',
        descripcion: 'Alcanzar una racha de 7 o más días consecutivos',
        desbloqueada: this.rachaMaximaUsuario >= 7
      },
      {
        icono: '🥇',
        nombre: 'Constancia de Oro',
        descripcion: 'Alcanzar una racha de 21 días consecutivos',
        desbloqueada: this.rachaMaximaUsuario >= 21
      },
      {
        icono: '🤝',
        nombre: 'Círculo de Confianza',
        descripcion: 'Vincular un Padrino de Hábito a un Desafío Premium',
        desbloqueada: tienePadrinoActivo
      },
      {
        icono: '🏆',
        nombre: 'Primer Desafío Cumplido',
        descripcion: 'Completar el 100% del plazo de un Desafío Premium',
        desbloqueada: tieneDesafioCumplido
      }
    ];
  }

  get habitosFiltrados(): Habit[] {
    if (this.comunidadSeleccionada === 'TODAS') {
      return this.habitos;
    }
    return this.habitos.filter((h: any) => (h.category || 'SALUD') === this.comunidadSeleccionada);
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

  traducirCategoria(cat?: string): string {
    const mapa: Record<string, string> = {
      SALUD: '🏋️ Salud y Fitness',
      ESTUDIO: '📚 Estudio y Lectura',
      PRODUCTIVIDAD: '⚡ Productividad',
      MINDFULNESS: '🧘 Mindfulness',
      FINANZAS: '💰 Finanzas'
    };
    return cat ? (mapa[cat] || cat) : '🏋️ Salud y Fitness';
  }

  porcentajeDesafioHabito(habito: any): number {
    const plazo = habito.duration_days || 21;
    const aprobados = habito.logs_aprobados_count || 0;
    return Math.min(100, Math.round((aprobados / plazo) * 100));
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

  errorEdicion = '';

  iniciarEdicion(habito: any) {
    this.error = '';
    this.errorEdicion = '';
    this.mensajeExito = '';
    this.habitoEditandoId = habito.id!;
    this.formEdicion = {
      name: habito.name || '',
      description: habito.description || '',
      category: habito.category || 'SALUD',
      duration_days: habito.duration_days || 21,
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
    this.error = '';
  }

  guardarEdicion(habitId: number) {
    if (!this.formEdicion.name.trim()) {
      this.error = 'El nombre del hábito no puede estar vacío.';
      return;
    }

    this.guardandoEdicion = true;
    this.error = '';
    this.mensajeExito = '';

    const payload: any = {
      name: this.formEdicion.name.trim(),
      description: this.formEdicion.description?.trim() || '',
      category: this.formEdicion.category,
      duration_days: Number(this.formEdicion.duration_days) || 21,
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
        this.error =
          err?.error?.is_premium?.[0] ||
          err?.error?.duration_days?.[0] ||
          this.mensajeErrorRegistro(err);
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
          this.mensajeExito = `✅ ¡Hábito "${habito.name}" completado hoy (+50 XP por Autodeclaración)!`;
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
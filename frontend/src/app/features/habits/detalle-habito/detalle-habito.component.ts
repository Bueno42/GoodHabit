import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { V1Service } from '../../../api/api/v1.service';
import { Habit } from '../../../api/model/habit';
import { HabitLog } from '../../../api/model/habitLog';

@Component({
  selector: 'app-detalle-habito',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './detalle-habito.component.html'
})
export class DetalleHabitoComponent implements OnInit {
  habitId!: number;
  habito: Habit | null = null;
  logsDelHabito: HabitLog[] = [];
  cargando = true;
  error = '';
  mensajeExito = '';

  // ABM #3: Estado para editar y eliminar registros del historial
  logEditandoId: number | null = null;
  guardandoLog = false;
  eliminandoLogId: number | null = null;
  formEdicionLog = {
    actual_value: 1,
    notes: ''
  };

  private route = inject(ActivatedRoute);
  private apiService = inject(V1Service);

  ngOnInit() {
    this.habitId = Number(this.route.snapshot.paramMap.get('id'));
    this.cargarDetalle();
  }

  cargarDetalle() {
    this.cargando = true;
    this.error = '';

    this.apiService.v1HabitsRetrieve(this.habitId).subscribe({
      next: (habitoData) => {
        this.habito = habitoData;
        this.cargarLogsDelHabito();
      },
      error: (err) => {
        console.error('Error al cargar el hábito', err);
        this.error = 'No se pudo encontrar el hábito solicitado.';
        this.cargando = false;
      }
    });
  }

  cargarLogsDelHabito() {
    this.apiService.v1LogsList().subscribe({
      next: (todosLosLogs) => {
        // Filtramos únicamente los registros que pertenecen a este hábito en particular
        this.logsDelHabito = todosLosLogs.filter(l => l.habit === this.habitId);
        this.cargando = false;
      },
      error: (err) => {
        console.error('Error al cargar historial del hábito', err);
        this.error = 'Error al cargar el historial de registros.';
        this.cargando = false;
      }
    });
  }


  get heatmapDias(): { fecha: string; estado: string }[] {
    const dias: { fecha: string; estado: string }[] = [];
    const hoy = new Date();
    
    // Mapeamos los logs existentes por fecha (YYYY-MM-DD)
    const mapaLogs = new Map<string, string>();
    for (const log of this.logsDelHabito || []) {
      if (log.date && log.estado) {
        mapaLogs.set(log.date, log.estado);
      }
    }

    // Generamos los últimos 30 días desde hace 29 días hasta hoy
    for (let i = 29; i >= 0; i--) {
      const fechaIter = new Date(hoy);
      fechaIter.setDate(hoy.getDate() - i);
      
      // Formato local YYYY-MM-DD para evitar desfases de zona horaria UTC
      const yyyy = fechaIter.getFullYear();
      const mm = String(fechaIter.getMonth() + 1).padStart(2, '0');
      const dd = String(fechaIter.getDate()).padStart(2, '0');
      const fechaStr = `${yyyy}-${mm}-${dd}`;

      dias.push({
        fecha: fechaStr,
        estado: mapaLogs.get(fechaStr) || 'SIN_REGISTRO'
      });
    }

    return dias;
  }

  // --- MÉTRICAS Y GRÁFICO ESPECÍFICO DEL HÁBITO ---
  get totalAprobados(): number {
    return this.logsDelHabito.filter(
      l => l.estado === 'APROBADO' || l.estado === 'TIMEOUT_APROBADO'
    ).length;
  }

  get tasaEfectividad(): number {
    if (!this.logsDelHabito.length) return 0;
    return Math.round((this.totalAprobados / this.logsDelHabito.length) * 100);
  }

  // Últimos 7 registros ordenados cronológicamente para el gráfico de barras del hábito
  get ultimosLogsGrafico(): HabitLog[] {
    return [...this.logsDelHabito].slice(0, 7).reverse();
  }

  calcularAlturaBarraLog(log: HabitLog): number {
    if (!this.habito) return 20;
    if (this.habito.goal_type === 'BOOL') {
      return (log.estado === 'APROBADO' || log.estado === 'TIMEOUT_APROBADO') ? 100 : 35;
    }
    const meta = this.habito.target_value || 1;
    const valor = log.actual_value ?? 0;
    const pct = Math.round((valor / meta) * 100);
    return Math.max(12, Math.min(100, pct));
  }

  colorBarraLog(estado?: string): string {
    if (estado === 'APROBADO' || estado === 'TIMEOUT_APROBADO') return '#10b981'; // Verde
    if (estado === 'EN_REVISION') return '#f59e0b'; // Amarillo
    if (estado === 'RECHAZADO') return '#ef4444'; // Rojo
    return '#9ca3af';
  }

  // --- ABM #2: Baja de Padrino en este hábito ---
  desvincularPadrino(asignacionId: number, padrinoUsername?: string) {
    if (!this.habito) return;
    const confirmar = window.confirm(`¿Querés desvincular a @${padrinoUsername || 'este padrino'} de "${this.habito.name}"?`);
    if (!confirmar) return;

    this.error = '';
    this.mensajeExito = '';

    this.apiService.v1PadrinazgosDestroy(asignacionId).subscribe({
      next: () => {
        this.mensajeExito = `Se desvinculó a @${padrinoUsername} del hábito.`;
        this.cargarDetalle();
      },
      error: (err) => {
        console.error('Error al desvincular padrino', err);
        this.error = 'No se pudo desvincular al padrino.';
      }
    });
  }

  // --- ABM #3: Modificación y Baja del Historial de Registros ---
  iniciarEdicionLog(log: HabitLog) {
    this.error = '';
    this.mensajeExito = '';
    this.logEditandoId = log.id!;
    this.formEdicionLog = {
      actual_value: log.actual_value ?? 1,
      notes: log.notes || ''
    };
  }

  cancelarEdicionLog() {
    this.logEditandoId = null;
  }

  guardarEdicionLog(log: HabitLog) {
    if (!log.id) return;
    this.guardandoLog = true;
    this.error = '';
    this.mensajeExito = '';

    const payload = {
      actual_value: this.formEdicionLog.actual_value,
      notes: this.formEdicionLog.notes?.trim() || ''
    };

    this.apiService.v1LogsPartialUpdate(log.id, payload).subscribe({
      next: (logActualizado) => {
        this.logsDelHabito = this.logsDelHabito.map(l => l.id === log.id ? logActualizado : l);
        this.logEditandoId = null;
        this.guardandoLog = false;
        this.mensajeExito = `Registro #${log.id} actualizado correctamente.`;
      },
      error: (err) => {
        console.error('Error al actualizar registro', err);
        this.error = 'No se pudo actualizar el registro.';
        this.guardandoLog = false;
      }
    });
  }

  eliminarLog(log: HabitLog) {
    if (!log.id || this.eliminandoLogId !== null) return;
    const confirmar = window.confirm(`¿Querés eliminar el registro del día ${log.date}?`);
    if (!confirmar) return;

    this.error = '';
    this.mensajeExito = '';
    this.eliminandoLogId = log.id;

    this.apiService.v1LogsDestroy(log.id).subscribe({
      next: () => {
        this.eliminandoLogId = null;
        this.mensajeExito = 'Registro eliminado correctamente.';
        this.cargarDetalle(); // Recarga la racha del hábito y el historial
      },
      error: (err) => {
        console.error('Error al eliminar registro', err);
        this.error = 'No se pudo eliminar el registro.';
        this.eliminandoLogId = null;
      }
    });
  }
}
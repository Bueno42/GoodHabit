import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { V1Service } from '../../api/api/v1.service'; 
import { HabitLog } from '../../api/model/habitLog';

@Component({
  selector: 'app-moderacion-padrino',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './moderacion-padrino.component.html',
  styleUrls: ['./moderacion-padrino.component.css']
})
export class ModeracionPadrinoComponent implements OnInit {
  logsPendientes: HabitLog[] = [];
  cargando = true;
  error = '';
  errorAccion = '';
  mensajeAccion = '';
  logEnProceso: number | null = null;
  
  // Usamos un diccionario para manejar el motivo de rechazo por cada log independientemente
  motivosRechazo: { [logId: number]: string } = {};

  private apiService = inject(V1Service);

  ngOnInit() {
    this.cargarPendientes();
  }

  cargarPendientes() {
    this.cargando = true;
    // IMPORTANTE: Revisá en tu v1.service.ts si el nombre quedó exactamente así.
    // Al agregar @extend_schema(many=True), el generador pudo haberle puesto "List" al final.
    this.apiService.v1LogsPendientesRevisionList().subscribe({
      next: (data: any) => {
        this.logsPendientes = data;
        this.cargando = false;
      },
      error: (err) => {
        console.error(err);
        this.error = 'Error al cargar las evidencias pendientes.';
        this.cargando = false;
      }
    });
  }

  esVideo(url: string | null | undefined): boolean {
    return !!url && /\.mp4(?:$|[?#])/i.test(url);
  }

  procesarEvidencia(logId: number, estado: 'APROBADO' | 'RECHAZADO') {
    if (this.logEnProceso !== null) {
      return;
    }

    this.errorAccion = '';
    this.mensajeAccion = '';
    const payload: any = { estado };
    
    if (estado === 'RECHAZADO') {
      const motivo = this.motivosRechazo[logId];
      if (!motivo || motivo.trim() === '') {
        this.errorAccion = 'Escribí un motivo antes de rechazar la evidencia.';
        return;
      }
      payload.motivo_rechazo = motivo.trim();
    }

    this.logEnProceso = logId;
    this.apiService.v1LogsModerarPartialUpdate(logId, payload).subscribe({
      next: () => {
        this.logsPendientes = this.logsPendientes.filter(log => log.id !== logId);
        this.mensajeAccion = estado === 'APROBADO'
          ? 'Evidencia aprobada correctamente.'
          : 'Evidencia rechazada. Se notificó el motivo.';
        this.logEnProceso = null;
      },
      error: (err) => {
        console.error('Error al procesar la evidencia', err);
        this.errorAccion = 'No se pudo guardar la decisión. Intentá nuevamente.';
        this.logEnProceso = null;
      }
    });
  }
}
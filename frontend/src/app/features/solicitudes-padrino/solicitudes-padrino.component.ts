import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { V1Service } from '../../api/api/v1.service';
import { HabitPadrino } from '../../api/model/habitPadrino';

@Component({
  selector: 'app-solicitudes-padrino',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './solicitudes-padrino.component.html',
  styleUrls: ['./solicitudes-padrino.component.css'] // Movés las clases genéricas a styles.css, acordate
})
export class SolicitudesPadrinoComponent implements OnInit {
  solicitudes: HabitPadrino[] = [];
  cargando = true;
  error = '';
  errorAccion = '';
  mensajeAccion = '';
  solicitudEnProceso: number | null = null;

  private apiService = inject(V1Service);

  ngOnInit() {
    this.cargarSolicitudes();
  }

  cargarSolicitudes() {
    this.cargando = true;
    this.apiService.v1PadrinazgosMisSolicitudesRetrieve().subscribe({
      next: (data: any) => {
        this.solicitudes = data;
        this.cargando = false;
      },
      error: (err) => {
        console.error('Error al cargar solicitudes', err);
        this.error = 'No se pudieron cargar las solicitudes.';
        this.cargando = false;
      }
    });
  }

  responderSolicitud(solicitudId: number, estado: 'ACEPTADO' | 'RECHAZADO') {
    if (this.solicitudEnProceso !== null) {
      return;
    }

    this.errorAccion = '';
    this.mensajeAccion = '';
    this.solicitudEnProceso = solicitudId;
    const payload = { estado_invitacion: estado };

    this.apiService.v1PadrinazgosPartialUpdate(solicitudId, payload).subscribe({
      next: () => {
        this.solicitudes = this.solicitudes.filter(s => s.id !== solicitudId);
        this.mensajeAccion = estado === 'ACEPTADO'
          ? 'Invitación aceptada. Ya podés acompañar este hábito.'
          : 'Invitación rechazada.';
        this.solicitudEnProceso = null;
      },
      error: (err) => {
        console.error('Error al responder', err);
        this.errorAccion = 'No se pudo guardar tu respuesta. Intentá nuevamente.';
        this.solicitudEnProceso = null;
      }
    });
  }
}
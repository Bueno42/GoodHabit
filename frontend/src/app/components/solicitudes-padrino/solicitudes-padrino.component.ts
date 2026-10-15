import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PadrinosService } from '../../services/padrinos.service';
import { HabitPadrino } from '../../models/padrino.interface'; // Importación correcta

@Component({
  selector: 'app-solicitudes-padrino',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './solicitudes-padrino.component.html',
  styleUrls: ['./solicitudes-padrino.component.css']
})
export class SolicitudesPadrinoComponent implements OnInit {
  public solicitudesPendientes: HabitPadrino[] = []; // Uso de la interfaz correcta

  constructor(private padrinosService: PadrinosService) {}

  ngOnInit(): void {
    this.cargarSolicitudes();
  }

  cargarSolicitudes(): void {
    this.padrinosService.obtenerPadrinazgos().subscribe({
      next: (data) => {
        // Validación contra el estado exacto del backend
        this.solicitudesPendientes = data.filter(p => p.estado_invitacion === 'PENDIENTE');
      },
      error: (err) => console.error('Error al cargar solicitudes', err)
    });
  }

  // Respetamos los literales que espera el servicio y el backend de Django
  responder(id: number, estado: 'ACEPTADO' | 'RECHAZADO'): void {
    this.padrinosService.responderSolicitud(id, estado).subscribe({
      next: () => this.cargarSolicitudes(),
      error: (err) => console.error('Error al responder solicitud', err)
    });
  }
}
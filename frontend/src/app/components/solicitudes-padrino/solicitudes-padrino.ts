import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PadrinosService, PadrinoSolicitud } from '../../services/padrinos';

@Component({
  selector: 'app-solicitudes-padrino',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './solicitudes-padrino.html',
  styleUrls: ['./solicitudes-padrino.css'] // o .scss
})
export class SolicitudesPadrinoComponent implements OnInit {
  public solicitudesPendientes: PadrinoSolicitud[] = [];

  constructor(private padrinosService: PadrinosService) {}

  ngOnInit(): void {
    this.cargarSolicitudes();
  }

  cargarSolicitudes(): void {
    this.padrinosService.obtenerPadrinazgos().subscribe({
      next: (data) => {
        this.solicitudesPendientes = data.filter(p => p.estado === 'Pendiente');
      },
      error: (err) => console.error('Error al cargar solicitudes', err)
    });
  }

  responder(id: number, estado: 'Aprobado' | 'Rechazado'): void {
    this.padrinosService.responderSolicitud(id, estado).subscribe({
      next: () => this.cargarSolicitudes(),
      error: (err) => console.error('Error al responder solicitud', err)
    });
  }
}
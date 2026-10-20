import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';


@Component({
  selector: 'app-solicitudes-padrino',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './solicitudes-padrino.component.html',
  styleUrl: './solicitudes-padrino.component.css'
})
export class SolicitudesPadrinoComponent  {
  /*
  public solicitudesPendientes: HabitPadrino[] = [];
  public mensaje: string = '';

  constructor(private padrinosService: PadrinosService) {}

  ngOnInit(): void {
    this.cargarSolicitudes();
  }

  cargarSolicitudes(): void {
    this.padrinosService.getMisSolicitudes().subscribe({
      next: (data) => {
        // Usa la variable definida arriba
        this.solicitudesPendientes = data;
      },
      error: (err) => console.error('Error al cargar solicitudes', err)
    });
  }

  // 2. El parámetro se llama padrinazgoId para coincidir con la llamada interna
  responder(padrinazgoId: number, estado: 'ACEPTADO' | 'RECHAZADO'): void {
    this.padrinosService.responderSolicitud(padrinazgoId, estado).subscribe({
      next: () => {
        this.mensaje = `Solicitud ${estado.toLowerCase()} con éxito.`;
        this.cargarSolicitudes();
      },
      error: (err) => {
        this.mensaje = err.error?.detail || 'Error al responder la solicitud.';
      }
    });
  }
  */  
}
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

  procesarEvidencia(logId: number, estado: 'APROBADO' | 'RECHAZADO') {
    const payload: any = { estado: estado };
    
    if (estado === 'RECHAZADO') {
      const motivo = this.motivosRechazo[logId];
      if (!motivo || motivo.trim() === '') {
        alert('Tenés que escribir un motivo para rechazar la evidencia.');
        return;
      }
      payload.motivo_rechazo = motivo;
    }

    this.apiService.v1LogsModerarPartialUpdate(logId, payload).subscribe({
      next: () => {
        // Sacamos el log de la lista visual sin recargar la página entera
        this.logsPendientes = this.logsPendientes.filter(log => log.id !== logId);
        alert(`Evidencia ${estado.toLowerCase()} con éxito.`);
      },
      error: (err) => {
        console.error('Error al procesar la evidencia', err);
        alert('Hubo un error al comunicar la decisión al servidor.');
      }
    });
  }
}
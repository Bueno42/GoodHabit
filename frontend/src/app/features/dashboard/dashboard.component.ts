import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { V1Service } from '../../api/api/v1.service'; 
import { Habit } from '../../api/model/habit';
import { RouterModule, Router } from '@angular/router'; // <-- Sumar Router
import { HttpErrorResponse } from '@angular/common/http';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  habitos: Habit[] = [];
  cargando = true;
  error = '';
  registrandoHabitId: number | null = null;

  private apiService = inject(V1Service);
  private router = inject(Router); // <-- Inyectar Router

  ngOnInit() {
    this.cargarHabitos();
  }

  cargarHabitos() {
    this.apiService.v1HabitsList().subscribe({
      next: (data) => {
        this.habitos = data;
        this.cargando = false;
      },
      error: (err) => {
        console.error(err);
        this.error = 'No se pudieron cargar los hábitos. ¿El interceptor mandó el token?';
        this.cargando = false;
      }
    });
  }

  // NUEVA LÓGICA DE NEGOCIO: Crear la transacción antes de pedir la foto
  registrarEjecucion(habitId: number) {
    if (this.registrandoHabitId !== null) {
      return;
    }

    this.error = '';
    this.registrandoHabitId = habitId;

    // Armamos el payload para el log. 
    // Tu HabitLogViewSet en Django ya inyecta el usuario y el estado inicial.
    const payload = {
      habit: habitId
    };

    // Suponiendo que tu servicio generado por OpenAPI se llama así:
    this.apiService.v1LogsCreate(payload).subscribe({
      next: (nuevoLog: any) => {
        this.registrandoHabitId = null;
        // Acá está la magia de la Opción A: 
        // Django creó el log y nos devolvió su ID real.
        // Ahora sí saltamos a la pantalla de S3 pasando el ID del log, no del hábito.
        this.router.navigate(['/evidencia', nuevoLog.id]);
      },
      error: (err) => {
        console.error('Error al generar el registro en el backend', {
          status: err.status,
          response: err.error
        });
        this.registrandoHabitId = null;
        this.error = this.mensajeErrorRegistro(err);
      }
    });
  }

  private mensajeErrorRegistro(err: HttpErrorResponse): string {
    if (err.status === 401) {
      return 'Tu sesión venció. Iniciá sesión nuevamente para registrar el hábito.';
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
      const serializedBody = JSON.stringify(body);
      if (serializedBody && serializedBody !== '{}') {
        return serializedBody;
      }
    }

    return `No se pudo iniciar el registro del hábito (HTTP ${err.status}).`;
  }
}
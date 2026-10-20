import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { V1Service } from '../../api/api/v1.service'; 
import { Habit } from '../../api/model/habit';
import { RouterModule, Router } from '@angular/router'; // <-- Sumar Router

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './dashboard.component.html'
})
export class DashboardComponent implements OnInit {
  habitos: Habit[] = [];
  cargando = true;
  error = '';

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
    // Armamos el payload para el log. 
    // Tu HabitLogViewSet en Django ya inyecta el usuario y el estado inicial.
    const payload = {
      habit: habitId
    };

    // Suponiendo que tu servicio generado por OpenAPI se llama así:
    this.apiService.v1LogsCreate(payload).subscribe({
      next: (nuevoLog: any) => {
        // Acá está la magia de la Opción A: 
        // Django creó el log y nos devolvió su ID real.
        // Ahora sí saltamos a la pantalla de S3 pasando el ID del log, no del hábito.
        this.router.navigate(['/evidencia', nuevoLog.id]);
      },
      error: (err) => {
        console.error('Error al generar el registro en el backend', err);
        this.error = 'No se pudo iniciar el registro del hábito de hoy.';
      }
    });
  }
}
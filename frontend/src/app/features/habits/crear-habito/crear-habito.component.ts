import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { V1Service } from '../../../api/api/v1.service'; 
import { HabitRequest } from '../../../api/model/habitRequest';

@Component({
  selector: 'app-crear-habito',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './crear-habito.component.html'
})
export class CrearHabitoComponent {
  nuevoHabito: HabitRequest = {
    name: '',
    frequency: 'DAILY',
    goal_type: 'BOOL',
    target_value: 1,
    is_active: true
  };
  
  cargando = false;
  error = '';

  private apiService = inject(V1Service);
  private router = inject(Router);

  guardarHabito() {
    if (!this.nuevoHabito.name) {
      this.error = 'El nombre del hábito es obligatorio.';
      return;
    }

    this.cargando = true;
    this.error = '';

    
    this.apiService.v1HabitsCreate(this.nuevoHabito).subscribe({
      next: () => {
        this.cargando = false;
        // Si sale bien, lo pateamos de vuelta al dashboard para que vea su hábito
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        console.error(err);
        this.error = 'Error al guardar el hábito en el servidor.';
        this.cargando = false;
      }
    });
  }
}
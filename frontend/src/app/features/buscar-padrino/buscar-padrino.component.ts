import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms'; // Necesario para el ngModel
import { V1Service } from '../../api/api/v1.service';
import { Habit } from '../../api/model/habit';

@Component({
  selector: 'app-buscar-padrino',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './buscar-padrino.component.html'
})
export class BuscarPadrinoComponent implements OnInit {
  misHabitos: Habit[] = [];
  usuariosEncontrados: any[] = []; // Reemplazá 'any' por tu interfaz de User autogenerada
  
  habitoSeleccionadoId: number | null = null;
  terminoBusqueda: string = '';
  
  private apiService = inject(V1Service);

  ngOnInit() {
    // Cargamos los hábitos del usuario para llenar el select
    this.apiService.v1HabitsList().subscribe({
      next: (data) => this.misHabitos = data,
      error: (err) => console.error('Error cargando hábitos', err)
    });
  }

  buscarUsuario() {
    if (this.terminoBusqueda.trim().length < 3) return; // No buscamos si pone 2 letritas

    // REVISÁ EL NOMBRE DEL MÉTODO: Seguramente sea v1UsersList
    // Pasamos el término de búsqueda según cómo lo acepte tu OpenAPI
    this.apiService.v1UsersList(this.terminoBusqueda).subscribe({
      next: (data) => this.usuariosEncontrados = data,
      error: (err) => console.error('Error buscando usuarios', err)
    });
  }

  enviarInvitacion(padrinoId: number) {
    if (!this.habitoSeleccionadoId) {
      alert('¡Tenés que seleccionar un hábito primero!');
      return;
    }

    const payload = {
      habit: this.habitoSeleccionadoId,
      padrino: padrinoId
      // estado_invitacion no se manda porque está read_only (y por defecto es PENDIENTE)
    };

    // REVISÁ EL NOMBRE DEL MÉTODO
    this.apiService.v1PadrinazgosCreate(payload).subscribe({
      next: () => {
        alert('Invitación enviada correctamente.');
        this.usuariosEncontrados = [];
        this.terminoBusqueda = '';
      },
      error: (err) => {
        // Acá atajamos los ValidationError que programaste en Django (ej: "límite de 2 padrinos")
        alert('No se pudo enviar. Revisá que el hábito no tenga ya 2 padrinos.');
        console.error(err);
      }
    });
  }
}
import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { V1Service } from '../../api/api/v1.service';
import { Habit } from '../../api/model/habit';
import { User } from '../../api/model/user';

@Component({
  selector: 'app-buscar-padrino',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './buscar-padrino.component.html',
  styleUrl: './buscar-padrino.component.css'
})
export class BuscarPadrinoComponent implements OnInit {
  misHabitos: Habit[] = [];
  usuariosEncontrados: User[] = [];

  habitoSeleccionadoId: number | null = null;
  terminoBusqueda = '';

  buscando = false;
  busquedaRealizada = false;
  enviandoUsuarioId: number | null = null;
  mensajeError = '';
  mensajeExito = '';

  private apiService = inject(V1Service);

  ngOnInit() {
    this.cargarHabitos();
  }

  cargarHabitos() {
    this.apiService.v1HabitsList().subscribe({
      next: (data) => {
        this.misHabitos = data;
      },
      error: (err) => {
        console.error('Error cargando hábitos', err);
        this.mensajeError = 'No se pudieron cargar tus hábitos.';
      }
    });
  }

  get habitoSeleccionado(): Habit | undefined {
    return this.misHabitos.find(h => h.id === this.habitoSeleccionadoId);
  }

  get cupoLleno(): boolean {
    const asignacionesActivas = (this.habitoSeleccionado?.padrino_assignments || []).filter(
      a => a.estado_invitacion === 'PENDIENTE' || a.estado_invitacion === 'ACEPTADO'
    );
    return asignacionesActivas.length >= 2;
  }

  estadoAsignacionUsuario(userId?: number): string | null {
    if (!userId || !this.habitoSeleccionado?.padrino_assignments) return null;
    const asignacion = this.habitoSeleccionado.padrino_assignments.find(
      a => a.padrino === userId && (a.estado_invitacion === 'PENDIENTE' || a.estado_invitacion === 'ACEPTADO')
    );
    return asignacion?.estado_invitacion || null;
  }

  buscarUsuario() {
    this.mensajeError = '';
    this.mensajeExito = '';

    const query = this.terminoBusqueda.trim();
    if (query.length < 2) {
      this.mensajeError = 'Ingresá al menos 2 caracteres para buscar por usuario o correo.';
      return;
    }

    this.buscando = true;
    this.busquedaRealizada = false;

    this.apiService.v1UsersList(query).subscribe({
      next: (data) => {
        this.usuariosEncontrados = data;
        this.buscando = false;
        this.busquedaRealizada = true;
      },
      error: (err) => {
        console.error('Error buscando usuarios', err);
        this.buscando = false;
        this.mensajeError = 'Ocurrió un error al buscar usuarios. Intentá nuevamente.';
      }
    });
  }

  enviarInvitacion(usuario: User) {
    if (!usuario.id || this.enviandoUsuarioId !== null) return;

    if (!this.habitoSeleccionadoId) {
      this.mensajeError = 'Seleccioná primero un hábito de la lista.';
      return;
    }

    this.mensajeError = '';
    this.mensajeExito = '';
    this.enviandoUsuarioId = usuario.id;

    this.apiService.v1PadrinazgosCreate({
      habit: this.habitoSeleccionadoId,
      padrino: usuario.id
    }).subscribe({
      next: () => {
        this.enviandoUsuarioId = null;
        this.mensajeExito = `Invitación enviada a @${usuario.username}. Queda pendiente de su aceptación.`;
        this.cargarHabitos(); // Actualiza los padrinos asignados del hábito en tiempo real
      },
      error: (err) => {
        console.error(err);
        this.enviandoUsuarioId = null;
        const body = err.error;
        const fieldMessages = body && typeof body === 'object'
          ? Object.values(body)
              .flatMap(value => Array.isArray(value) ? value : [value])
              .filter((value): value is string => typeof value === 'string')
          : [];
        this.mensajeError = typeof body?.detail === 'string'
          ? body.detail
          : fieldMessages[0] ?? 'No se pudo enviar la invitación.';
      }
    });
  }
}
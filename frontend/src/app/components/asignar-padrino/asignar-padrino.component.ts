import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { PadrinosService } from '../../services/padrinos.service';
import { CommonModule } from '@angular/common'; // Importación limpia
import { FormsModule } from '@angular/forms';
import { HabitPadrino } from '../../models/padrino.interface';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-asignar-padrino',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './asignar-padrino.component.html',
  styleUrls: ['./asignar-padrino.component.css'] // Corregido typo: styleUrl -> styleUrls
})
export class AsignarPadrinoComponent implements OnInit, OnDestroy { // Agregado sufijo Component
  @Input() habitId!: number;
  @Input() currentUserId!: number; // Necesario para evitar auto-asignación visual

  public padrinosActivos: HabitPadrino[] = [];
  public usuarioSeleccionadoId: number | null = null;
  public errorMensaje: string = '';

  // Subject para manejar la limpieza de suscripciones y evitar Memory Leaks
  private destroy$ = new Subject<void>();

  constructor(private padrinosService: PadrinosService) {}

  ngOnInit(): void {
    if (!this.habitId || !this.currentUserId) {
      console.warn('AsignarPadrinoComponent requiere habitId y currentUserId');
    }
    this.cargarPadrinos();
  }

  ngOnDestroy(): void {
    // Matamos todas las suscripciones vivas al destruir el componente
    this.destroy$.next();
    this.destroy$.complete();
  }

  cargarPadrinos(): void {
    this.padrinosService.obtenerPadrinazgos()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: HabitPadrino[]) => {
          // Filtramos solo los que pertenecen a este hábito y no fueron rechazados
          this.padrinosActivos = data.filter(p => 
            p.id === this.habitId && 
            p.estado_invitacion !== 'RECHAZADO' // Corregido: Mayúsculas y nombre correcto
          );
        },
        error: (err) => console.error('Error al cargar la lista de padrinos', err)
      });
  }

  invitar(): void {
    this.errorMensaje = '';

    // Validación 1: Campo vacío
    if (!this.usuarioSeleccionadoId) {
      this.errorMensaje = 'Debe ingresar el ID del usuario a invitar.';
      return;
    }

    // Validación 2: Auto-asignación
    if (this.usuarioSeleccionadoId === this.currentUserId) {
      this.errorMensaje = 'No podés asignarte como padrino de tu propio hábito.';
      return;
    }

    // Validación 3: Límite de cupo (Defensa en profundidad)
    if (this.padrinosActivos.length >= 2) {
      this.errorMensaje = 'Este hábito ya alcanzó el límite máximo de 2 padrinos.';
      return;
    }

    // Petición al backend
    this.padrinosService.invitarPadrino(this.habitId, this.usuarioSeleccionadoId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.usuarioSeleccionadoId = null; // Limpiar input
          this.cargarPadrinos(); // Refrescar lista visual
        },
        error: (err) => {
          // Capturamos la clave 'error' exacta que manda el backend de Django
          this.errorMensaje = err.error?.error || 'Ocurrió un error al enviar la invitación.';
        }
      });
  }
}
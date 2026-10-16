import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { PadrinosService } from '../../services/padrinos.service';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HabitPadrino } from '../../models/padrino.interface';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Component({
  selector: 'app-asignar-padrino',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './asignar-padrino.component.html',
  styleUrls: ['./asignar-padrino.component.css']
})
export class AsignarPadrinoComponent implements OnInit, OnDestroy {
  @Input() habitId: number = 1; // Valor por defecto para pruebas
  @Input() currentUserId: number = 1; // Valor por defecto para pruebas

  public padrinosActivos: HabitPadrino[] = [];
  public usuarioSeleccionadoId: number | null = null;
  public errorMensaje: string = '';

  private destroy$ = new Subject<void>();

  constructor(private padrinosService: PadrinosService) {}

  ngOnInit(): void {
    if (!this.habitId || !this.currentUserId) {
      console.warn('AsignarPadrinoComponent requiere habitId y currentUserId');
    }
    this.cargarPadrinos();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  cargarPadrinos(): void {
    // Si tenés getPadrinosDeHabito(id), usalo directamente. 
    // Si usás obtenerPadrinazgos(), filtramos por el id del hábito:
    this.padrinosService.obtenerPadrinazgos()
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (data: HabitPadrino[]) => {
          this.padrinosActivos = data.filter(p => {
            const habitoId = p.habito || p.habit || p.habito_id;
            const estado = p.estado || p.estado_invitacion;
            
            // Si la API ya te trae solo los del hábito actual, quita la validación habitoId
            return (habitoId === undefined || habitoId === this.habitId) && estado !== 'RECHAZADO';
          });
        },
        error: (err) => console.error('Error al cargar la lista de padrinos', err)
      });
  }

  invitar(): void {
    this.errorMensaje = '';

    if (!this.usuarioSeleccionadoId) {
      this.errorMensaje = 'Debe ingresar el ID del usuario a invitar.';
      return;
    }

    if (Number(this.usuarioSeleccionadoId) === Number(this.currentUserId)) {
      this.errorMensaje = 'No podés asignarte como padrino de tu propio hábito.';
      return;
    }

    if (this.padrinosActivos.length >= 2) {
      this.errorMensaje = 'Este hábito ya alcanzó el límite máximo de 2 padrinos.';
      return;
    }

    this.padrinosService.invitarPadrino(this.habitId, this.usuarioSeleccionadoId)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: () => {
          this.usuarioSeleccionadoId = null;
          this.cargarPadrinos();
        },
        error: (err) => {
          // Soporta tanto err.error.detail como err.error.error
          this.errorMensaje = err.error?.detail || err.error?.error || 'Ocurrió un error al enviar la invitación.';
        }
      });
  }
}
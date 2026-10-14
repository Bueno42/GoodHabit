import { Component, Input, OnInit } from '@angular/core';
import { PadrinosService, PadrinoSolicitud } from '../../services/padrinos';
import { CommonModule } from '../../../../node_modules/@angular/common/types/_common_module-chunk';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-asignar-padrino',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './asignar-padrino.html',
  styleUrl: './asignar-padrino.css',
})
export class AsignarPadrino implements OnInit{
  @Input() habitId!: number;
  @Input() currentUserId!: number;

  public padrinosActivos: PadrinoSolicitud[] = [];
  public usuarioSeleccionadoId: number | null = null;
  public errorMensaje: string = '';

  constructor(private padrinosService: PadrinosService) {}

  ngOnInit(): void {
    this.cargarPadrinos();
  }

  cargarPadrinos(): void {
    this.padrinosService.obtenerPadrinazgos().subscribe({
      next: (data) => {
        this.padrinosActivos = data.filter(p => p.habit === this.habitId && p.estado !== 'Rechazado');
      },
      error: (err) => console.error('Error al cargar padrinos, err')
    });
  }

  invitar(): void{
    this.errorMensaje = '';

    if (!this.usuarioSeleccionadoId){
      this.errorMensaje = 'No podes asignarte a vos mismo como padrino.';
      return;
    }

    if (this.padrinosActivos.length >= 2){
      this.errorMensaje = 'Un habito solo puede tener hasta 2 padrinos.';
      return;
    }

    this.padrinosService.invitarPadrino(this.habitId, this.usuarioSeleccionadoId).subscribe({
      next: () => {
        this.usuarioSeleccionadoId = null;
        this.cargarPadrinos();
      },
      error: (err) => {
        this.errorMensaje = err.error?.detail || 'Error al enviar la invitacion.';
      }
    });

  }

}

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { V1Service } from '../../../api/api/v1.service';
import { HabitRequest } from '../../../api/model/habitRequest';

@Component({
  selector: 'app-crear-habito',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './crear-habito.component.html',
  styleUrl: './crear-habito.component.css'
})
export class CrearHabitoComponent implements OnInit {
  nuevoHabito: HabitRequest & {
    is_premium?: boolean;
    category?: string;
    duration_days?: number;
  } = {
    name: '',
    description: '',
    category: 'SALUD' as any,
    duration_days: 21,
    frequency: 'DAILY',
    custom_days: [],
    goal_type: 'BOOL',
    target_value: 1,
    unit: '',
    is_premium: false,
    is_active: true
  };

  readonly diasSemana = [
    { valor: 6, etiqueta: 'D', nombre: 'Domingo' },
    { valor: 0, etiqueta: 'L', nombre: 'Lunes' },
    { valor: 1, etiqueta: 'M', nombre: 'Martes' },
    { valor: 2, etiqueta: 'M', nombre: 'Miércoles' },
    { valor: 3, etiqueta: 'J', nombre: 'Jueves' },
    { valor: 4, etiqueta: 'V', nombre: 'Viernes' },
    { valor: 5, etiqueta: 'S', nombre: 'Sábado' }
  ];

  cargando = false;
  error = '';

  esCuentaPremium = false;
  cuposDisponibles = 0;
  habitosPremiumActivos = 0;
  readonly MAX_PREMIUM = 2; 
  mostrarModalMercadoPago = false;
  procesandoPago = false;
  datosTarjeta = {
    numero: '4509 9500 1234 5678',
    titular: 'USUARIO DEMO UTN',
    vencimiento: '12/29',
    cvv: '123'
  };

  private apiService = inject(V1Service);
  private router = inject(Router);

  ngOnInit() {
    this.esCuentaPremium = localStorage.getItem(this.obtenerClaveStorage('premium')) === 'true';
    this.cuposDisponibles = Number(localStorage.getItem(this.obtenerClaveStorage('cupos_disponibles')) || '0');

    this.apiService.v1HabitsList().subscribe({
      next: (habitos) => {
        this.habitosPremiumActivos = habitos.filter(h => h.is_premium).length;
        // Si ya tiene 2 activos, cualquier cupo sobrante en storage se limpia
        if (this.habitosPremiumActivos >= this.MAX_PREMIUM) {
          this.cuposDisponibles = 0;
          localStorage.setItem(this.obtenerClaveStorage('cupos_disponibles'), '0');
        }
      }
    });

  }

  get cuposRestantesPorComprar(): number {
    return Math.max(0, this.MAX_PREMIUM - (this.habitosPremiumActivos + this.cuposDisponibles));
  }

  private obtenerClaveStorage(clave: string): string {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload?.user_id) {
          return `goodhabit_${clave}_user_${payload.user_id}`;
        }
      } catch {
        // Fallback si el token no se puede decodificar
      }
    }
    return `goodhabit_${clave}_default`;
  }

  seleccionarModalidad(esPremium: boolean) {
    if (!esPremium) {
      this.nuevoHabito.is_premium = false;
      return;
    }

    if (this.habitosPremiumActivos >= this.MAX_PREMIUM) {
      this.error = 'Alcanzaste el límite máximo de 2 Desafíos Premium activos en simultáneo.';
      return;
    }

    if (this.cuposDisponibles <= 0) {
      this.mostrarModalMercadoPago = true;
      return;
    }

    this.nuevoHabito.is_premium = true;
  }

  abrirModalMercadoPago() {
    this.mostrarModalMercadoPago = true;
  }

  cerrarModalMercadoPago() {
    if (this.procesandoPago) return;
    this.mostrarModalMercadoPago = false;
  }

  confirmarPagoMercadoPago(cantidadCupos: 1 | 2 = 1) {
    if (this.procesandoPago) return;
    const comprables = Math.min(cantidadCupos, this.cuposRestantesPorComprar);
    if (comprables <= 0) {
      this.mostrarModalMercadoPago = false;
      this.error = 'Ya alcanzaste el límite máximo de 2 Desafíos Premium.';
      return;
    }

    this.procesandoPago = true;
    setTimeout(() => {
      this.cuposDisponibles += comprables;
      localStorage.setItem(this.obtenerClaveStorage('premium'), 'true');
      localStorage.setItem(this.obtenerClaveStorage('cupos_disponibles'), String(this.cuposDisponibles));
      this.esCuentaPremium = true;
      this.nuevoHabito.is_premium = true;
      this.procesandoPago = false;
      this.mostrarModalMercadoPago = false;
    }, 1400);
  }

  alternarDiaPersonalizado(dia: number) {
    const diasSeleccionados = this.nuevoHabito.custom_days ?? [];
    this.nuevoHabito.custom_days = diasSeleccionados.includes(dia)
      ? diasSeleccionados.filter(diaSeleccionado => diaSeleccionado !== dia)
      : [...diasSeleccionados, dia].sort((a, b) => a - b);
    this.error = '';
  }

  guardarHabito() {
    if (!this.nuevoHabito.name || !this.nuevoHabito.name.trim()) {
      this.error = 'El nombre del hábito es obligatorio.';
      return;
    }

    if (this.nuevoHabito.is_premium && this.habitosPremiumActivos >= this.MAX_PREMIUM) {
      this.error = 'Alcanzaste el límite máximo de 2 Desafíos Premium activos en simultáneo.';
      return;
    }

    if (this.nuevoHabito.is_premium && this.cuposDisponibles <= 0) {
      this.mostrarModalMercadoPago = true;
      return;
    }

    if (this.nuevoHabito.frequency === 'CUSTOM' && !this.nuevoHabito.custom_days?.length) {
      this.error = 'Seleccioná al menos un día para la frecuencia personalizada.';
      return;
    }

    this.cargando = true;
    this.error = '';

    const payload: any = {
      ...this.nuevoHabito,
      name: this.nuevoHabito.name.trim(),
      description: this.nuevoHabito.description?.trim() || '',
      category: this.nuevoHabito.category || 'SALUD',
      duration_days: Number(this.nuevoHabito.duration_days) || 21,
      target_value: this.nuevoHabito.goal_type === 'BOOL' ? 1 : (this.nuevoHabito.target_value || 1),
      unit: this.nuevoHabito.goal_type === 'BOOL' ? '' : (this.nuevoHabito.unit?.trim() || ''),
      is_premium: !!this.nuevoHabito.is_premium
    };

    this.apiService.v1HabitsCreate(payload as HabitRequest).subscribe({
      next: () => {
        if (payload.is_premium){
          const restantes = Math.max(0, this.cuposDisponibles - 1);
          this.cuposDisponibles = restantes
          localStorage.setItem(this.obtenerClaveStorage('cupos_disponibles'), String(restantes));
        }
        this.cargando = false;
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
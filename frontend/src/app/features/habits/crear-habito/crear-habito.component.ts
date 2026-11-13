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
    goal_type: 'BOOL',
    target_value: 1,
    unit: '',
    is_premium: false,
    is_active: true
  };

  cargando = false;
  error = '';

  // Estado de Cuenta Premium y Pasarela Simulada (Mercado Pago)
  esCuentaPremium = false;
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
    this.esCuentaPremium = localStorage.getItem(this.obtenerClaveStoragePremium()) === 'true';
  }

  private obtenerClaveStoragePremium(): string {
    const token = localStorage.getItem('access_token');
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (payload?.user_id) {
          return `goodhabit_premium_user_${payload.user_id}`;
        }
      } catch {
        // Fallback si el token no se puede decodificar
      }
    }
    return 'goodhabit_premium_default';
  }

  seleccionarModalidad(esPremium: boolean) {
    if (esPremium && !this.esCuentaPremium) {
      this.mostrarModalMercadoPago = true;
      return;
    }
    this.nuevoHabito.is_premium = esPremium;
  }

  abrirModalMercadoPago() {
    this.mostrarModalMercadoPago = true;
  }

  cerrarModalMercadoPago() {
    if (this.procesandoPago) return;
    this.mostrarModalMercadoPago = false;
  }

  confirmarPagoMercadoPago() {
    if (this.procesandoPago) return;
    this.procesandoPago = true;

    setTimeout(() => {
      localStorage.setItem(this.obtenerClaveStoragePremium(), 'true');
      this.esCuentaPremium = true;
      this.nuevoHabito.is_premium = true;
      this.procesandoPago = false;
      this.mostrarModalMercadoPago = false;
    }, 1400);
  }

  guardarHabito() {
    if (!this.nuevoHabito.name || !this.nuevoHabito.name.trim()) {
      this.error = 'El nombre del hábito es obligatorio.';
      return;
    }

    if (this.nuevoHabito.is_premium && !this.esCuentaPremium) {
      this.mostrarModalMercadoPago = true;
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
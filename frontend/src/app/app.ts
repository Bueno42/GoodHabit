import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterOutlet, RouterLink, RouterLinkActive, NavigationEnd } from '@angular/router';
import { filter, forkJoin, of, catchError } from 'rxjs';
import { V1Service } from './api/api/v1.service';

export interface AlertaNotificacion {
  icono: string;
  titulo: string;
  detalle: string;
  ruta: string;
  color: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit {
  private readonly themeStorageKey = 'goodhabit-theme';
  private router = inject(Router);
  private apiService = inject(V1Service);

  menuAbierto = false;
  modoOscuro = false;
  esPantallaPublica = false;

  // Contadores para los puntitos rojos del Sidebar y Centro de Notificaciones
  habitosPendientesCount = 0;
  invitacionesPendientesCount = 0;
  moderacionesPendientesCount = 0;
  notificacionesAbiertas = false;
  listaNotificaciones: AlertaNotificacion[] = [];

  get totalNotificaciones(): number {
    return this.habitosPendientesCount + this.invitacionesPendientesCount + this.moderacionesPendientesCount;
  }

  ngOnInit(): void {
    const temaGuardado = localStorage.getItem(this.themeStorageKey);
    this.modoOscuro = temaGuardado === 'dark';

    this.actualizarEstadoRuta();
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe(() => {
        this.actualizarEstadoRuta();
        this.notificacionesAbiertas = false;
      });
  }

  private actualizarEstadoRuta(): void {
    const url = this.router.url;
    this.esPantallaPublica = url.startsWith('/login') || url.startsWith('/registro');
    if (this.esPantallaPublica) {
      this.menuAbierto = false;
      this.notificacionesAbiertas = false;
    } else if (localStorage.getItem('access_token')) {
      this.cargarIndicadoresNotificaciones();
    }
  }

  cargarIndicadoresNotificaciones(): void {
    forkJoin({
      habitos: this.apiService.v1HabitsList().pipe(catchError(() => of([]))),
      invitaciones: (this.apiService as any).v1PadrinosMisSolicitudesRetrieve
        ? (this.apiService as any).v1PadrinosMisSolicitudesRetrieve().pipe(catchError(() => of([])))
        : of([]),
      moderaciones: (this.apiService as any).v1LogsPendientesRevisionRetrieve
        ? (this.apiService as any).v1LogsPendientesRevisionRetrieve().pipe(catchError(() => of([])))
        : of([])
    }).subscribe(({ habitos, invitaciones, moderaciones }: any) => {
      const listaHabitos = Array.isArray(habitos) ? habitos : [];
      const listaInvitaciones = Array.isArray(invitaciones) ? invitaciones : [];
      const listaModeraciones = Array.isArray(moderaciones) ? moderaciones : [];

      // Hábitos que aún no fueron completados ni están en revisión hoy (o fueron rechazados)
      const pendientesHoy = listaHabitos.filter(
        (h: any) => !h.estado_hoy || h.estado_hoy === 'RECHAZADO'
      );
      const rechazadosHoy = listaHabitos.filter((h: any) => h.estado_hoy === 'RECHAZADO');

      this.habitosPendientesCount = pendientesHoy.length;
      this.invitacionesPendientesCount = listaInvitaciones.length;
      this.moderacionesPendientesCount = listaModeraciones.length;

      const alertas: AlertaNotificacion[] = [];

      if (rechazadosHoy.length > 0) {
        alertas.push({
          icono: '❌',
          titulo: `${rechazadosHoy.length} evidencia(s) rechazada(s) hoy`,
          detalle: 'Revisá el motivo del padrino en tu Dashboard y volvé a subir evidencia antes de la 01:00 AM.',
          ruta: '/dashboard',
          color: '#fef2f2'
        });
      }

      if (pendientesHoy.length - rechazadosHoy.length > 0) {
        const cant = pendientesHoy.length - rechazadosHoy.length;
        alertas.push({
          icono: '🏠',
          titulo: `${cant} hábito(s) pendiente(s) de completar hoy`,
          detalle: 'Completá tu jornada para sumar +50 XP y mantener tu racha activa.',
          ruta: '/dashboard',
          color: '#eff6ff'
        });
      }

      if (this.invitacionesPendientesCount > 0) {
        alertas.push({
          icono: '📨',
          titulo: `${this.invitacionesPendientesCount} invitación(es) de padrinazgo`,
          detalle: 'Un usuario quiere sumarte a su Círculo de Confianza.',
          ruta: '/solicitudes',
          color: '#fefce8'
        });
      }

      if (this.moderacionesPendientesCount > 0) {
        alertas.push({
          icono: '⚖️',
          titulo: `${this.moderacionesPendientesCount} evidencia(s) esperando tu revisión`,
          detalle: 'Tus ahijados subieron pruebas a S3. Evaluálas antes del timeout de 24hs.',
          ruta: '/moderacion',
          color: '#f0fdf4'
        });
      }

      this.listaNotificaciones = alertas;
    });
  }

  alternarNotificaciones(): void {
    this.notificacionesAbiertas = !this.notificacionesAbiertas;
    if (this.notificacionesAbiertas) {
      this.cargarIndicadoresNotificaciones();
    }
  }

  irANotificacion(ruta: string): void {
    this.notificacionesAbiertas = false;
    this.router.navigate([ruta]);
  }

  alternarMenu(): void {
    if (this.esPantallaPublica) return;
    this.menuAbierto = !this.menuAbierto;
  }

  cerrarMenu(): void {
    this.menuAbierto = false;
  }

  alternarTema(): void {
    this.modoOscuro = !this.modoOscuro;
    localStorage.setItem(this.themeStorageKey, this.modoOscuro ? 'dark' : 'light');
  }

  cerrarSesion(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.menuAbierto = false;
    this.notificacionesAbiertas = false;
    this.router.navigate(['/login']);
  }
}
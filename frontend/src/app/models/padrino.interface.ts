export interface HabitPadrino {
  id: number;
  padrino: number;
  padrino_username: string;
  estado_invitacion: 'PENDIENTE' | 'ACEPTADO' | 'RECHAZADO';
  fecha_asignacion: string;
}
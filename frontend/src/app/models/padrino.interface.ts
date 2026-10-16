export interface HabitPadrino {
  id: number;
  habito?: number;
  habito_id?: number;
  habit?: number; // Propiedad opcional para evitar choque de tipos
  padrino: number;
  padrino_nombre?: string;
  padrino_username?: string;
  estado: 'PENDIENTE' | 'ACEPTADO' | 'RECHAZADO';
  estado_invitacion?: 'PENDIENTE' | 'ACEPTADO' | 'RECHAZADO';
}
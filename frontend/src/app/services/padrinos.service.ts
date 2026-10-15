import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment.development';
import { HabitPadrino } from '../models/padrino.interface';

@Injectable({
  providedIn: 'root'
})
export class PadrinosService {
  private apiUrl = environment.apiUrl; // Usamos la base limpia: http://localhost:8000/api/v1

  constructor(private http: HttpClient) {}

  // Pega a HabitPadrinoViewSet
  getMisSolicitudes(): Observable<HabitPadrino[]> {
    return this.http.get<HabitPadrino[]>(`${this.apiUrl}/padrinazgos/mis-solicitudes/`);
  }

  // Pega a HabitPadrinoViewSet (ruta base del ModelViewSet / GenericViewSet)
  obtenerPadrinazgos(): Observable<HabitPadrino[]> {
    return this.http.get<HabitPadrino[]>(`${this.apiUrl}/padrinazgos/`);
  }

  // Pega a HabitViewSet (La invitación nace desde el hábito)
  invitarPadrino(habitId: number, padrinoId: number): Observable<HabitPadrino> {
    return this.http.post<HabitPadrino>(`${this.apiUrl}/habits/${habitId}/invitar-padrino/`, {
      padrino_id: padrinoId // Asegurate de que esta key coincida con request.data.get('padrino_id') en Django
    });
  }

  // Pega a HabitPadrinoViewSet (Endpoint de acción custom)
  responderSolicitud(padrinazgoId: number, estado: 'ACEPTADO' | 'RECHAZADO'): Observable<any> {
    return this.http.patch(`${this.apiUrl}/padrinazgos/${padrinazgoId}/responder/`, {
      estado: estado
    });
  }
}
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface PadrinoSolicitud {
  id?: number;
  habit: number;
  padrino: number;
  padrino_username?: string;
  estado: 'Pendiente' | 'Aprobado' | 'Rechazado';
}



@Injectable({
  providedIn: 'root',
})
export class PadrinosService {
  private apiUrl = '/api/padrinazgos/';

  constructor(private http: HttpClient) {}

  obtenerPadrinazgos(): Observable<PadrinoSolicitud[]> {
    return this.http.get<PadrinoSolicitud[]>(this.apiUrl);
  }

  invitarPadrino(habitId: number, padrinoId: number): Observable<PadrinoSolicitud> {
    return this.http.post<PadrinoSolicitud>(this.apiUrl, {
      habit: habitId,
      padrino: padrinoId
    })
  }

  responderSolicitud(padrinazgoId: number, estado: 'Aprobado' | 'Rechazado'): Observable<PadrinoSolicitud> {
    return this.http.patch<PadrinoSolicitud>(`${this.apiUrl}${padrinazgoId}/`, {
      estado: estado
    });
  }

}

import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CrearHabitoComponent } from './features/habits/crear-habito/crear-habito.component';
import { SubirEvidenciaComponent } from './features/habits/subir-evidencia/subir-evidencia.component';
import { ModeracionPadrinoComponent } from './features/moderacion-padrino/moderacion-padrino.component';
import { SolicitudesPadrinoComponent } from './features/solicitudes-padrino/solicitudes-padrino.component';
import { BuscarPadrinoComponent } from './features/buscar-padrino/buscar-padrino.component';
import { authGuard } from './auth.guard';
import { DetalleHabitoComponent } from './features/habits/detalle-habito/detalle-habito.component';
import { RegistroComponent } from './features/auth/registro/registro.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'crear-habito', component: CrearHabitoComponent, canActivate: [authGuard] },
  { path: 'evidencia/:id', component: SubirEvidenciaComponent, canActivate: [authGuard] },
  { path: 'moderacion', component: ModeracionPadrinoComponent, canActivate: [authGuard] },
  { path: 'solicitudes', component: SolicitudesPadrinoComponent, canActivate: [authGuard] },
  { path: 'buscar-padrino', component: BuscarPadrinoComponent, canActivate: [authGuard] },
  { path: 'habitos/:id', component: DetalleHabitoComponent },
  { path: 'registro', component: RegistroComponent },
];
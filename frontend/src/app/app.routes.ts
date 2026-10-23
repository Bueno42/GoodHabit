import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CrearHabitoComponent } from './features/habits/crear-habito/crear-habito.component';
import { SubirEvidenciaComponent } from './features/habits/subir-evidencia/subir-evidencia.component';
import { ModeracionPadrinoComponent } from './features/moderacion-padrino/moderacion-padrino.component';
import { SolicitudesPadrinoComponent } from './features/solicitudes-padrino/solicitudes-padrino.component';
import { BuscarPadrinoComponent } from './features/buscar-padrino/buscar-padrino.component';


export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'crear-habito', component: CrearHabitoComponent },
  { path: 'evidencia/:id', component: SubirEvidenciaComponent },
  {path: 'moderacion', component: ModeracionPadrinoComponent},
  { path: 'solicitudes', component: SolicitudesPadrinoComponent },
  { path: 'buscar-padrino', component: BuscarPadrinoComponent },
];
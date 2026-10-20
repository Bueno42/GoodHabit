import { Routes } from '@angular/router';
import { LoginComponent } from './features/auth/login/login.component';
import { DashboardComponent } from './features/dashboard/dashboard.component';
import { CrearHabitoComponent } from './features/habits/crear-habito/crear-habito.component';
import { SubirEvidenciaComponent } from './features/habits/subir-evidencia/subir-evidencia.component';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: 'dashboard', component: DashboardComponent },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: 'crear-habito', component: CrearHabitoComponent },
  { path: 'evidencia/:id', component: SubirEvidenciaComponent }
];
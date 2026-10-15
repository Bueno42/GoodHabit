import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { AsignarPadrinoComponent } from './components/asignar-padrino/asignar-padrino.component';
import { SolicitudesPadrinoComponent } from './components/solicitudes-padrino/solicitudes-padrino.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet, 
    AsignarPadrinoComponent, 
    SolicitudesPadrinoComponent,
  ],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class AppComponent {
  title = 'frontend';
}
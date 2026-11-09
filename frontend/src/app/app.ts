import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class AppComponent {
  title = 'frontend';
  menuAbierto = false;
  modoOscuro = localStorage.getItem('goodhabit-theme') === 'dark';

  alternarMenu() {
    this.menuAbierto = !this.menuAbierto;
  }

  cerrarMenu() {
    this.menuAbierto = false;
  }

  alternarTema() {
    this.modoOscuro = !this.modoOscuro;
    localStorage.setItem('goodhabit-theme', this.modoOscuro ? 'dark' : 'light');
  }
}
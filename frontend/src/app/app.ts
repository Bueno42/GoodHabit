import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class AppComponent {
  private router = inject(Router);

  title = 'frontend';
  menuAbierto = false;
  modoOscuro = localStorage.getItem('goodhabit-theme') === 'dark';

  get esLogin(): boolean {
    return this.router.url.startsWith('/login');
  }

  alternarMenu() {
    this.menuAbierto = !this.menuAbierto;
  }

  cerrarMenu() {
    this.menuAbierto = false;
  }

  cerrarSesion() {
    localStorage.removeItem('access_token');
    this.cerrarMenu();
    this.router.navigate(['/login'], { replaceUrl: true });
  }

  alternarTema() {
    this.modoOscuro = !this.modoOscuro;
    localStorage.setItem('goodhabit-theme', this.modoOscuro ? 'dark' : 'light');
  }
}
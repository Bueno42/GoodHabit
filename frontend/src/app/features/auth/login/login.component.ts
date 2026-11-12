import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TokenService } from '../../../api/api/token.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  username = '';
  password = '';
  errorMessage = '';
  cargando = false;

  private tokenService = inject(TokenService);
  private router = inject(Router);

  login() {
    if (this.cargando) return;

    if (!this.username.trim() || !this.password) {
      this.errorMessage = 'Completá todos los campos.';
      return;
    }

    this.errorMessage = '';
    this.cargando = true;

    this.tokenService.tokenCreate({ username: this.username.trim(), password: this.password }).subscribe({
      next: (response) => {
        localStorage.setItem('access_token', response.access);
        this.cargando = false;
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        console.error(err);
        this.cargando = false;
        this.errorMessage = 'Credenciales inválidas o servidor caído.';
      }
    });
  }
}
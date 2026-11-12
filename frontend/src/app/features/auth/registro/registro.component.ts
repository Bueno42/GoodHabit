import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { V1Service } from '../../../api/api/v1.service';
import { TokenService } from '../../../api/api/token.service';

@Component({
  selector: 'app-registro',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './registro.component.html'
})
export class RegistroComponent {
  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  errorMessage = '';
  cargando = false;

  private apiService = inject(V1Service);
  private tokenService = inject(TokenService);
  private router = inject(Router);

  registrar() {
    this.errorMessage = '';

    if (!this.username.trim() || !this.email.trim() || !this.password) {
      this.errorMessage = 'Completá todos los campos obligatorios.';
      return;
    }

    if (this.password.length < 6) {
      this.errorMessage = 'La contraseña debe tener al menos 6 caracteres.';
      return;
    }

    if (this.password !== this.confirmPassword) {
      this.errorMessage = 'Las contraseñas no coinciden.';
      return;
    }

    this.cargando = true;

    this.apiService.v1UsersCreate({
      username: this.username.trim(),
      email: this.email.trim(),
      password: this.password
    }).subscribe({
      next: () => {
        // Auto-login inmediato tras registrarse
        this.tokenService.tokenCreate({
          username: this.username.trim(),
          password: this.password
        }).subscribe({
          next: (tokens) => {
            localStorage.setItem('access_token', tokens.access);
            this.cargando = false;
            this.router.navigate(['/dashboard']);
          },
          error: () => {
            this.cargando = false;
            this.router.navigate(['/login']);
          }
        });
      },
      error: (err) => {
        console.error('Error al registrar usuario', err);
        this.cargando = false;
        const body = err.error;
        if (body?.username) {
          this.errorMessage = `Usuario: ${body.username[0]}`;
        } else if (body?.email) {
          this.errorMessage = `Email: ${body.email[0]}`;
        } else if (body?.password) {
          this.errorMessage = `Contraseña: ${body.password[0]}`;
        } else {
          this.errorMessage = 'No se pudo completar el registro. Verificá los datos.';
        }
      }
    });
  }
}
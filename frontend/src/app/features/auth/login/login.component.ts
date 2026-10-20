import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
// ATENCIÓN: Verificá que esta ruta coincida con tu carpeta autogenerada
import { TokenService } from '../../../api/api/token.service'; 

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.component.html'
})
export class LoginComponent {
  username = '';
  password = '';
  errorMessage = '';

  private tokenService = inject(TokenService);
  private router = inject(Router);

  login() {
    if (!this.username || !this.password) {
      this.errorMessage = 'Completá todos los campos.';
      return;
    }

    // Le pegamos al backend usando la interfaz autogenerada de Swagger
    this.tokenService.tokenCreate({ username: this.username, password: this.password }).subscribe({
      next: (response) => {
        // Si el backend responde OK, guardamos el token de acceso
        localStorage.setItem('access_token', response.access);
        
        // Redirigimos al usuario al dashboard (que armaremos después)
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        console.error(err);
        this.errorMessage = 'Credenciales inválidas o servidor caído.';
      }
    });
  }
}
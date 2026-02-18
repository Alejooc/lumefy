import { Component, inject } from '@angular/core';
import { RouterModule, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuthService, UserRegister } from 'src/app/core/services/auth.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-auth-register',
  standalone: true,
  imports: [RouterModule, CommonModule, FormsModule],
  templateUrl: './auth-register.component.html',
  styleUrl: './auth-register.component.scss'
})
export class AuthRegisterComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  isLoading = false;
  userData: UserRegister = {
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    company_name: ''
  };

  SignUpOptions = [
    {
      image: 'assets/images/authentication/google.svg',
      name: 'Google'
    },
    {
      image: 'assets/images/authentication/twitter.svg',
      name: 'Twitter'
    },
    {
      image: 'assets/images/authentication/facebook.svg',
      name: 'Facebook'
    }
  ];

  register() {
    if (!this.userData.first_name || !this.userData.last_name || !this.userData.email || !this.userData.password || !this.userData.company_name) {
      Swal.fire('Error', 'Por favor completa todos los campos requeridos', 'error');
      return;
    }

    this.isLoading = true;
    this.authService.register(this.userData).subscribe({
      next: () => {
        this.isLoading = false;
        Swal.fire({
          icon: 'success',
          title: '¡Bienvenido!',
          text: 'Tu cuenta ha sido creada exitosamente.',
          timer: 1500,
          showConfirmButton: false
        }).then(() => {
          this.router.navigate(['/dashboard']);
        });
      },
      error: (err) => {
        this.isLoading = false;
        const msg = err.error?.detail || 'Error al registrar usuario';
        Swal.fire('Error', msg, 'error');
      }
    });
  }
}

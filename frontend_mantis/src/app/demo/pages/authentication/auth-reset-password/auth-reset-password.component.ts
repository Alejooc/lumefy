import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from 'src/app/core/services/api.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-auth-reset-password',
    standalone: true,
    imports: [CommonModule, RouterModule, ReactiveFormsModule],
    templateUrl: './auth-reset-password.component.html',
    styleUrls: ['./auth-reset-password.component.scss']
})
export class AuthResetPasswordComponent implements OnInit {
    private fb = inject(FormBuilder);
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private apiService = inject(ApiService);

    token = '';
    loading = false;

    resetPasswordForm = this.fb.group({
        new_password: ['', [Validators.required, Validators.minLength(6)]],
        confirm_password: ['', [Validators.required]]
    });

    ngOnInit() {
        this.route.queryParams.subscribe(params => {
            this.token = params['token'];
            if (!this.token) {
                Swal.fire('Error', 'Token de restablecimiento inválido o faltante.', 'error').then(() => {
                    this.router.navigate(['/login']);
                });
            }
        });
    }

    onSubmit() {
        if (this.resetPasswordForm.invalid) {
            return;
        }

        const { new_password, confirm_password } = this.resetPasswordForm.value;

        if (new_password !== confirm_password) {
            Swal.fire('Error', 'Las contraseñas no coinciden.', 'warning');
            return;
        }

        this.loading = true;
        this.apiService.post('/reset-password', { token: this.token, new_password }).subscribe({
            next: () => {
                this.loading = false;
                Swal.fire('Éxito', 'Contraseña actualizada correctamente. Inicia sesión con tu nueva clave.', 'success').then(() => {
                    this.router.navigate(['/login']);
                });
            },
            error: (err) => {
                this.loading = false;
                Swal.fire('Error', err?.error?.detail || 'El token ha expirado o es inválido.', 'error');
            }
        });
    }
}

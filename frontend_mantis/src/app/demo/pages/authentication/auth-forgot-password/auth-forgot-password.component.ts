import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from 'src/app/core/services/api.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-auth-forgot-password',
    standalone: true,
    imports: [CommonModule, RouterModule, ReactiveFormsModule],
    templateUrl: './auth-forgot-password.component.html',
    styleUrls: ['./auth-forgot-password.component.scss']
})
export class AuthForgotPasswordComponent {
    private fb = inject(FormBuilder);
    private apiService = inject(ApiService);

    forgotPasswordForm = this.fb.group({
        email: ['', [Validators.required, Validators.email]]
    });

    loading = false;
    sent = false;

    onSubmit() {
        if (this.forgotPasswordForm.invalid) {
            return;
        }

        this.loading = true;
        const email = this.forgotPasswordForm.get('email')?.value;

        this.apiService.post(`/password-recovery/${email}`, {}).subscribe({
            next: () => {
                this.loading = false;
                this.sent = true;
                Swal.fire('Enviado', 'Si el correo existe, recibirás instrucciones para restablecer tu contraseña.', 'success');
            },
            error: () => {
                this.loading = false;
                // Security: Always show success message to prevent email enumeration
                this.sent = true;
                Swal.fire('Enviado', 'Si el correo existe, recibirás instrucciones para restablecer tu contraseña.', 'success');
            }
        });
    }
}

import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router } from '@angular/router';
import { AdminService } from '../admin.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { UserService } from '../../users/user.service';
import { AuthService } from 'src/app/core/services/auth.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-admin-user-list',
    standalone: true,
    imports: [CommonModule, RouterModule, SharedModule],
    templateUrl: './admin-user-list.component.html'
})
export class AdminUserListComponent implements OnInit {
    users: any[] = [];
    loading = false;

    private adminService = inject(AdminService);
    private userService = inject(UserService);
    private authService = inject(AuthService);
    private router = inject(Router);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadUsers();
    }

    loadUsers() {
        this.loading = true;
        this.adminService.getUsers().subscribe({
            next: (data) => {
                this.users = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    impersonate(user: any) {
        Swal.fire({
            title: '¿Iniciar sesión como este usuario?',
            text: `Entrarás a la cuenta de ${user.full_name} (${user.email})`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, entrar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.adminService.impersonateUser(user.id).subscribe({
                    next: (res) => {
                        // Store new token
                        localStorage.setItem('access_token', res.access_token);

                        // Fetch new user (impersonated)
                        this.authService.fetchMe().subscribe(() => {
                            Swal.fire(
                                '¡Conectado!',
                                `Ahora eres ${res.user.email}`,
                                'success'
                            ).then(() => {
                                // Redirect to dashboard
                                this.router.navigate(['/dashboard']);
                            });
                        });
                    },
                    error: (err) => {
                        this.loading = false;
                        Swal.fire('Error', err.error?.detail || 'No se pudo iniciar sesión', 'error');
                        this.cdr.detectChanges();
                    }
                });
            }
        });
    }

    sendRecoveryEmail(user: any) {
        Swal.fire({
            title: '¿Enviar correo de recuperación?',
            text: `Se enviará un enlace para restablecer la contraseña a ${user.email}`,
            icon: 'info',
            showCancelButton: true,
            confirmButtonText: 'Sí, enviar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.userService.sendRecoveryEmail(user.id).subscribe({
                    next: () => {
                        Swal.fire('Enviado', 'El correo de recuperación ha sido enviado.', 'success');
                    },
                    error: (err) => {
                        console.error(err);
                        Swal.fire('Error', 'No se pudo enviar el correo.', 'error');
                    }
                });
            }
        });
    }
}

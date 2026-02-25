import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { AdminService } from '../admin.service';
import { AuthService } from 'src/app/core/services/auth.service';
import Swal from 'sweetalert2';

interface Company {
    id: string;
    name: string;
    logo_url?: string;
    tax_id?: string;
    plan?: 'FREE' | 'PRO' | 'ENTERPRISE' | string;
    is_active?: boolean;
    email?: string;
    valid_until?: string;
}

@Component({
    selector: 'app-company-list',
    standalone: false, // Part of AdminModule
    templateUrl: './company-list.component.html'
})
export class CompanyListComponent implements OnInit {
    companies: Company[] = [];
    loading = false;

    private api = inject(ApiService);
    private adminService = inject(AdminService);
    private authService = inject(AuthService);
    private router = inject(Router);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadCompanies();
    }

    loadCompanies() {
        this.loading = true;
        this.api.get<Company[]>('/admin/companies').subscribe({
            next: (data) => {
                this.companies = data;
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

    impersonate(company: Company) {
        Swal.fire({
            title: '¿Iniciar sesión como administrador?',
            text: `Entrarás a la cuenta de ${company.name}`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, entrar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.adminService.impersonateCompany(company.id).subscribe({
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

    extendSubscription(company: Company) {
        Swal.fire({
            title: 'Extender Suscripción',
            html: `
                <p>Empresa: <b>${company.name}</b></p>
                <p>Vence actualmente: ${company.valid_until ? company.valid_until.split('T')[0] : 'Indefinido'}</p>
                <label>Nueva Fecha de Vencimiento:</label>
                <input type="date" id="swal-input1" class="swal2-input" value="${company.valid_until ? company.valid_until.split('T')[0] : ''}">
            `,
            focusConfirm: false,
            showCancelButton: true,
            confirmButtonText: 'Guardar',
            preConfirm: () => {
                const date = (document.getElementById('swal-input1') as HTMLInputElement).value;
                if (!date) {
                    Swal.showValidationMessage('Selecciona una fecha');
                }
                return { valid_until: date };
            }
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.adminService.extendSubscription(company.id, result.value).subscribe({
                    next: () => {
                        Swal.fire('Actualizado', 'La suscripción ha sido extendida', 'success');
                        this.loadCompanies(); // Reload list
                        this.cdr.detectChanges();
                    },
                    error: () => {
                        this.loading = false;
                        Swal.fire('Error', 'No se pudo actualizar', 'error');
                        this.cdr.detectChanges();
                    }
                });
            }
        });
    }
}

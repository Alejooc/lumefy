import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-company-form',
    standalone: false,
    templateUrl: './company-form.component.html'
})
export class CompanyFormComponent implements OnInit {
    companyForm: FormGroup;
    isEditMode = false;
    companyId: string | null = null;
    loading = false;

    private fb = inject(FormBuilder);
    private api = inject(ApiService);
    private route = inject(ActivatedRoute);
    private router = inject(Router);

    constructor() {
        this.companyForm = this.fb.group({
            name: ['', Validators.required],
            tax_id: [''],
            address: [''],
            email: ['', [Validators.required, Validators.email]],
            phone: [''],
            plan: ['FREE', Validators.required],
            valid_until: [''],
            is_active: [true],
            // Admin user fields (only for create mode)
            admin_name: ['Administrador', Validators.required],
            admin_email: ['', [Validators.required, Validators.email]],
            admin_password: ['', [Validators.required, Validators.minLength(6)]]
        });
    }

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            this.companyId = params.get('id');
            if (this.companyId) {
                this.isEditMode = true;
                this.loadCompany(this.companyId);
                // Remove admin fields validation in edit mode
                this.companyForm.get('admin_name')?.clearValidators();
                this.companyForm.get('admin_email')?.clearValidators();
                this.companyForm.get('admin_password')?.clearValidators();
                this.companyForm.get('admin_name')?.updateValueAndValidity();
                this.companyForm.get('admin_email')?.updateValueAndValidity();
                this.companyForm.get('admin_password')?.updateValueAndValidity();
            }
        });
    }

    loadCompany(id: string) {
        this.loading = true;
        this.api.get<any>(`/admin/companies`).subscribe({
            next: (companies: any[]) => {
                const company = companies.find((c: any) => c.id === id);
                if (company) {
                    this.companyForm.patchValue(company);
                }
                this.loading = false;
            },
            error: (err) => {
                this.loading = false;
                console.error(err);
            }
        });
    }

    onSubmit() {
        if (this.companyForm.invalid) return;

        this.loading = true;
        const data = this.companyForm.value;

        if (this.isEditMode && this.companyId) {
            // Remove admin fields from update payload
            const { admin_name, admin_email, admin_password, ...updateData } = data;
            this.api.put(`/admin/companies/${this.companyId}`, updateData).subscribe({
                next: () => {
                    Swal.fire('Actualizado', 'Empresa actualizada correctamente', 'success');
                    this.router.navigate(['/admin/companies']);
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo actualizar', 'error');
                }
            });
        } else {
            this.api.post('/admin/companies', data).subscribe({
                next: (res: any) => {
                    Swal.fire({
                        icon: 'success',
                        title: '¡Empresa Creada!',
                        html: `
                            <p>La empresa <strong>${data.name}</strong> ha sido creada exitosamente.</p>
                            <hr>
                            <p><strong>Datos de acceso del administrador:</strong></p>
                            <p>📧 Email: <code>${data.admin_email}</code></p>
                            <p>🔑 Contraseña: <code>${data.admin_password}</code></p>
                            <p>🏢 Sucursal: Sede Principal</p>
                        `
                    });
                    this.router.navigate(['/admin/companies']);
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo crear: ' + (err.error?.detail || err.message), 'error');
                }
            });
        }
    }
}

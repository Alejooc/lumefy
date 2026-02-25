import { Component, OnInit, inject } from '@angular/core';

import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import Swal from 'sweetalert2';

interface Company {
    id: string;
    name: string;
    valid_until?: string;
}

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
        this.api.get<Company[]>(`/admin/companies`).subscribe({
            next: (companies: Company[]) => {
                const company = companies.find((c: Company) => c.id === id);
                if (company) {
                    if (company.valid_until) {
                        company.valid_until = company.valid_until.split('T')[0]; // Format YYYY-MM-DD for input[date]
                    }
                    this.companyForm.patchValue(company);
                }
                this.loading = false;
            },
            error: (error: unknown) => {
                this.loading = false;
                console.error(error);
            }
        });
    }

    onSubmit() {
        if (this.companyForm.invalid) return;

        this.loading = true;
        const data = this.companyForm.value;

        if (this.isEditMode && this.companyId) {
            // Remove admin fields from update payload
            const updateData = { ...data };
            delete updateData.admin_name;
            delete updateData.admin_email;
            delete updateData.admin_password;
            this.api.put(`/admin/companies/${this.companyId}`, updateData).subscribe({
                next: () => {
                    Swal.fire('Actualizado', 'Empresa actualizada correctamente', 'success');
                    this.router.navigate(['/admin/companies']);
                },
                error: () => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo actualizar', 'error');
                }
            });
        } else {
            this.api.post('/admin/companies', data).subscribe({
                next: () => {
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

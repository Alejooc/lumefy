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
            is_active: [true]
        });
    }

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            this.companyId = params.get('id');
            if (this.companyId) {
                this.isEditMode = true;
                this.loadCompany(this.companyId);
            }
        });
    }

    loadCompany(id: string) {
        this.loading = true;
        this.api.get<any>(`/admin/companies`).subscribe({ // Ideally get single company endpoint
            next: (companies: any[]) => {
                // Mocking get single by filtering list as we didn't implement get /companies/{id} in admin but we did implement put /companies/{id}
                // Actually we should have implemented get-one. Let's assume list for now or just fetch list and find.
                const company = companies.find(c => c.id === id);
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
            this.api.put(`/admin/companies/${this.companyId}`, data).subscribe({
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
                next: () => {
                    Swal.fire('Creado', 'Empresa creada correctamente', 'success');
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

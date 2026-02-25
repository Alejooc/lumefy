import { Component, OnInit, inject } from '@angular/core';

import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import Swal from 'sweetalert2';

interface BranchFormItem {
    id: string;
    name: string;
    address?: string;
    phone?: string;
    is_warehouse: boolean;
    allow_pos: boolean;
}

@Component({
    selector: 'app-branch-form',
    standalone: true,
    imports: [ReactiveFormsModule, RouterModule],
    templateUrl: './branch-form.component.html'
})
export class BranchFormComponent implements OnInit {
    branchForm: FormGroup;
    isEditMode = false;
    branchId: string | null = null;
    loading = false;

    private fb = inject(FormBuilder);
    private api = inject(ApiService);
    private route = inject(ActivatedRoute);
    private router = inject(Router);

    constructor() {
        this.branchForm = this.fb.group({
            name: ['', Validators.required],
            address: [''],
            phone: [''],
            is_warehouse: [true],
            allow_pos: [true]
        });
    }

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            this.branchId = params.get('id');
            if (this.branchId) {
                this.isEditMode = true;
                this.loadBranch(this.branchId);
            }
        });
    }

    loadBranch(id: string) {
        this.loading = true;
        this.api.get<BranchFormItem[]>(`/branches`).subscribe({
            next: (branches: BranchFormItem[]) => {
                const branch = branches.find((b: BranchFormItem) => b.id === id);
                if (branch) {
                    this.branchForm.patchValue(branch);
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
        if (this.branchForm.invalid) return;

        this.loading = true;
        const data = this.branchForm.value;

        if (this.isEditMode && this.branchId) {
            this.api.put(`/branches/${this.branchId}`, data).subscribe({
                next: () => {
                    Swal.fire('Actualizado', 'Sucursal actualizada', 'success');
                    this.router.navigate(['/branches']);
                },
                error: () => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo actualizar', 'error');
                }
            });
        } else {
            this.api.post('/branches', data).subscribe({
                next: () => {
                    Swal.fire('Creado', 'Sucursal creada', 'success');
                    this.router.navigate(['/branches']);
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo crear: ' + (err.error?.detail || err.message), 'error');
                }
            });
        }
    }
}

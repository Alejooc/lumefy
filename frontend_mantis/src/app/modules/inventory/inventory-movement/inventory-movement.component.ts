import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { HttpParams } from '@angular/common/http';
import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { ApiService } from '../../../core/services/api.service';
import { Branch } from '../../../core/services/branch.service';
import { Product } from '../../../core/services/product.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { InventoryMovement, InventoryService } from '../inventory.service';

interface InventoryMovementFormValue {
    product_id: string;
    branch_id: string;
    type: InventoryMovement['type'];
    quantity: number;
    reason?: string;
    reference_id?: string;
    destination_branch_id?: string | null;
}

@Component({
    selector: 'app-inventory-movement',
    templateUrl: './inventory-movement.component.html',
    styleUrls: ['./inventory-movement.component.scss'],
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, SharedModule]
})
export class InventoryMovementComponent implements OnInit {
    private fb = inject(FormBuilder);
    private api = inject(ApiService);
    private inventoryService = inject(InventoryService);
    private swal = inject(SweetAlertService);
    private router = inject(Router);
    private cdr = inject(ChangeDetectorRef);

    movementForm: FormGroup;
    products: Product[] = [];
    branches: Branch[] = [];
    filteredBranches: Branch[] = [];
    isLoading = false;
    isSubmitting = false;
    productSearchInput$ = new Subject<string>();

    constructor() {
        this.movementForm = this.fb.group({
            product_id: ['', Validators.required],
            branch_id: ['', Validators.required],
            type: ['IN', Validators.required],
            quantity: [1, [Validators.required, Validators.min(0.001)]],
            reason: [''],
            reference_id: [''],
            destination_branch_id: [null]
        });

        this.movementForm.get('type')?.valueChanges.subscribe((value: InventoryMovement['type']) => {
            const destinationControl = this.movementForm.get('destination_branch_id');
            if (value === 'TRF') {
                destinationControl?.setValidators([Validators.required]);
            } else {
                destinationControl?.clearValidators();
                this.movementForm.patchValue({ destination_branch_id: null });
            }
            destinationControl?.updateValueAndValidity();
        });
    }

    ngOnInit(): void {
        this.loadProducts();
        this.loadBranches();

        this.productSearchInput$
            .pipe(debounceTime(400), distinctUntilChanged())
            .subscribe((term) => this.loadProducts(term));
    }

    onSearch(event: { term: string; items: unknown[] }) {
        void event.items;
        if (event.term) {
            this.productSearchInput$.next(event.term);
        }
    }

    loadProducts(search = '') {
        this.isLoading = true;
        let params = new HttpParams();
        if (search) {
            params = params.set('search', search);
        }

        this.api.get<Product[]>('/products', params).subscribe({
            next: (data) => {
                this.products = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.isLoading = false;
            }
        });
    }

    loadBranches() {
        this.api.get<Branch[]>('/branches').subscribe({
            next: (data) => {
                this.branches = data;
                if (data.length === 1) {
                    this.movementForm.patchValue({ branch_id: data[0].id });
                }

                const currentBranchId = this.movementForm.get('branch_id')?.value as string;
                if (currentBranchId) {
                    this.updateFilteredBranches(currentBranchId);
                }
                this.cdr.detectChanges();
            },
            error: (error: unknown) => {
                console.error('Error loading branches', error);
            }
        });

        this.movementForm.get('branch_id')?.valueChanges.subscribe((value: string) => {
            this.updateFilteredBranches(value);
        });
    }

    updateFilteredBranches(sourceId: string) {
        this.filteredBranches = sourceId ? this.branches.filter((b) => b.id !== sourceId) : [];
        const currentDestinationId = this.movementForm.get('destination_branch_id')?.value as string | null;
        if (currentDestinationId === sourceId) {
            this.movementForm.patchValue({ destination_branch_id: null });
        }
    }

    onSubmit() {
        if (!this.movementForm.valid) return;

        this.isSubmitting = true;
        const payload = this.movementForm.value as InventoryMovementFormValue;
        this.inventoryService.createMovement(payload).subscribe({
            next: (result) => {
                this.isSubmitting = false;
                const typeLabels: Record<InventoryMovement['type'], string> = {
                    IN: 'Entrada',
                    OUT: 'Salida',
                    ADJ: 'Ajuste',
                    TRF: 'Transferencia'
                };
                const movementTypeName = typeLabels[payload.type];

                let message = `${movementTypeName} de ${payload.quantity} unidades registrada.`;
                if (payload.type !== 'TRF') {
                    message += `\nStock anterior: ${result.previous_stock} -> Nuevo stock: ${result.new_stock}`;
                } else {
                    message += '\nTransferencia enviada exitosamente.';
                }

                this.swal.success('Movimiento Registrado', message);
                this.router.navigate(['/inventory']);
            },
            error: (err: { error?: { detail?: string } }) => {
                this.isSubmitting = false;
                const detail = err?.error?.detail || 'No se pudo registrar el movimiento.';
                this.swal.error('Error', detail);
                this.cdr.detectChanges();
            }
        });
    }

    cancel() {
        this.router.navigate(['/inventory']);
    }
}

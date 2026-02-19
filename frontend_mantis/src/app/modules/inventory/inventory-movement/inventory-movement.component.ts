import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { InventoryService } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { SharedModule } from '../../../theme/shared/shared.module';

import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { HttpParams } from '@angular/common/http';

@Component({
    selector: 'app-inventory-movement',
    templateUrl: './inventory-movement.component.html',
    styleUrls: ['./inventory-movement.component.scss'],
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, SharedModule]
})
export class InventoryMovementComponent implements OnInit {
    movementForm: FormGroup;
    products: any[] = [];
    branches: any[] = [];
    isLoading = false;
    isSubmitting = false;
    productSearchInput$ = new Subject<string>();

    constructor(
        private fb: FormBuilder,
        private api: ApiService,
        private inventoryService: InventoryService,
        private swal: SweetAlertService,
        private router: Router,
        private cdr: ChangeDetectorRef
    ) {
        this.movementForm = this.fb.group({
            product_id: ['', Validators.required],
            branch_id: ['', Validators.required],
            type: ['IN', Validators.required],
            quantity: [1, [Validators.required, Validators.min(0.001)]],
            reason: [''],
            reference_id: [''],
            destination_branch_id: [null] // Added for TRF
        });

        // Dynamic validation for TRF
        this.movementForm.get('type')?.valueChanges.subscribe(val => {
            const destControl = this.movementForm.get('destination_branch_id');
            if (val === 'TRF') {
                destControl?.setValidators([Validators.required]);
            } else {
                destControl?.clearValidators();
            }
            destControl?.updateValueAndValidity();
        });
    }

    ngOnInit(): void {
        this.loadProducts();
        this.loadBranches();

        // Setup search debounce
        this.productSearchInput$.pipe(
            debounceTime(400),
            distinctUntilChanged()
        ).subscribe(term => {
            this.loadProducts(term);
        });
    }

    onSearch(event: { term: string, items: any[] }) {
        if (event.term) {
            this.productSearchInput$.next(event.term);
        }
    }

    loadProducts(search: string = '') {
        this.isLoading = true;
        let params = new HttpParams();
        if (search) {
            params = params.set('search', search);
        }

        this.api.get<any[]>('/products', params).subscribe({
            next: (data) => {
                this.products = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => this.isLoading = false
        });
    }

    loadBranches() {
        this.api.get<any[]>('/branches').subscribe({
            next: (data) => {
                this.branches = data;
                // Auto-select if only one branch
                if (data.length === 1) {
                    this.movementForm.patchValue({ branch_id: data[0].id });
                }

                // Trigger filter update initially if value exists
                const current = this.movementForm.get('branch_id')?.value;
                if (current) this.updateFilteredBranches(current);

                this.cdr.detectChanges();
            },
            error: (err) => console.error('Error loading branches', err)
        });

        // Listen for branch_id changes to filter destination branches
        this.movementForm.get('branch_id')?.valueChanges.subscribe(val => {
            this.updateFilteredBranches(val);
        });
    }

    // ... (rest of methods)

    // ... (rest of methods)

    // ... (rest of methods)

    // ...

    // ...

    filteredBranches: any[] = [];

    updateFilteredBranches(sourceId: string) {
        if (!sourceId) {
            this.filteredBranches = [];
        } else {
            this.filteredBranches = this.branches.filter(b => b.id !== sourceId);
        }
        // If current destination is the same as new source, clear it
        const currentDest = this.movementForm.get('destination_branch_id')?.value;
        if (currentDest === sourceId) {
            this.movementForm.patchValue({ destination_branch_id: null });
        }
    }

    onSubmit() {
        if (this.movementForm.valid) {
            this.isSubmitting = true;
            this.inventoryService.createMovement(this.movementForm.value).subscribe({
                next: (result) => {
                    this.isSubmitting = false;
                    const typeLabels: any = { IN: 'Entrada', OUT: 'Salida', ADJ: 'Ajuste', TRF: 'Transferencia' };
                    const typeName = typeLabels[this.movementForm.value.type] || this.movementForm.value.type;

                    let msg = `${typeName} de ${this.movementForm.value.quantity} unidades registrada.`;
                    if (this.movementForm.value.type !== 'TRF') {
                        msg += `\nStock anterior: ${result.previous_stock} → Nuevo stock: ${result.new_stock}`;
                    } else {
                        msg += `\nTransferencia enviada exitosamente.`;
                    }

                    this.swal.success(
                        'Movimiento Registrado',
                        msg
                    );
                    this.router.navigate(['/inventory']);
                },
                error: (err) => {
                    this.isSubmitting = false;
                    console.error(err);
                    const detail = err?.error?.detail || 'No se pudo registrar el movimiento.';
                    this.swal.error('Error', detail);
                    this.cdr.detectChanges();
                }
            });
        }
    }

    cancel() {
        this.router.navigate(['/inventory']);
    }
}

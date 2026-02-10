import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { InventoryService } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { SharedModule } from '../../../theme/shared/shared.module';

import { Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs/operators';
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
        private router: Router
    ) {
        this.movementForm = this.fb.group({
            product_id: ['', Validators.required],
            branch_id: ['7a287434-466e-4919-b25b-c9b09f87be81', Validators.required], // Default Branch
            type: ['IN', Validators.required],
            quantity: [1, [Validators.required, Validators.min(0.001)]],
            reason: [''],
            reference_id: ['']
        });
    }

    ngOnInit(): void {
        this.loadProducts();

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
            },
            error: () => this.isLoading = false
        });
    }

    onSubmit() {
        if (this.movementForm.valid) {
            this.isSubmitting = true;
            this.inventoryService.createMovement(this.movementForm.value).subscribe({
                next: () => {
                    this.isSubmitting = false;
                    this.swal.success('Éxito', 'Movimiento registrado correctamente.');
                    this.router.navigate(['/inventory']);
                },
                error: (err) => {
                    this.isSubmitting = false;
                    console.error(err);
                    this.swal.error('Error', 'No se pudo registrar el movimiento.');
                }
            });
        }
    }

    cancel() {
        this.router.navigate(['/inventory']);
    }
}

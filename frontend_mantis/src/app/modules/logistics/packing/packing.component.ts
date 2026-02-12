import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { NgbModal, NgbNavModule } from '@ng-bootstrap/ng-bootstrap';
import Swal from 'sweetalert2';
import { SaleService, Sale } from '../../../core/services/sale.service';
import { LogisticsService, SalePackage, PackageType } from '../logistics.service';

@Component({
    selector: 'app-packing',
    standalone: true,
    imports: [CommonModule, RouterModule, FormsModule, ReactiveFormsModule, NgbNavModule],
    templateUrl: './packing.component.html'
})
export class PackingComponent implements OnInit {
    saleId: string | null = null;
    sale: Sale | null = null;
    packages: SalePackage[] = [];
    packageTypes: PackageType[] = [];
    loading = false;
    activeTab = 1;

    // Package Creation
    packageForm: FormGroup;
    selectedPackageType: PackageType | null = null;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private saleService = inject(SaleService);
    private logisticsService = inject(LogisticsService);
    private fb = inject(FormBuilder);
    private modalService = inject(NgbModal);
    private cdr = inject(ChangeDetectorRef);

    constructor() {
        this.packageForm = this.fb.group({
            package_type_id: [null, Validators.required],
            tracking_number: [''],
            weight: [0],
            items: this.fb.array([]) // Complex handling omitted for brevity, logic below
        });
    }

    ngOnInit() {
        this.saleId = this.route.snapshot.paramMap.get('id');
        if (this.saleId) {
            this.loadData();
        }
    }

    loadData() {
        this.loading = true;
        // Load Sale, Packages, Types in parallel
        this.saleService.getSale(this.saleId!).subscribe(s => {
            this.sale = s;
            this.cdr.detectChanges();
        });
        this.logisticsService.getPackageTypes().subscribe(t => {
            this.packageTypes = t;
            this.cdr.detectChanges();
        });
        this.logisticsService.getPackages(this.saleId!).subscribe({
            next: (p) => {
                this.packages = p;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    // Helper calculate unpacked items
    getUnpackedItems() {
        if (!this.sale) return [];
        // Map picked items
        const items = this.sale.items.map((i: any) => ({ ...i, packed: 0 }));

        // Deduct packed
        this.packages.forEach(pkg => {
            pkg.items.forEach(pi => {
                const item = items.find(i => i.id === pi.sale_item_id);
                if (item) item.packed += pi.quantity;
            });
        });

        // Return items with remaining > 0
        return items.filter(i => (i.quantity_picked || 0) - i.packed > 0);
    }

    get itemsFormArray() {
        return this.packageForm.get('items') as any;
    }

    createPackage(content: any) {
        this.selectedPackageType = null;
        this.packageForm.reset();

        // Clear existing items in FormArray
        const itemsControl = this.packageForm.get('items') as any;
        itemsControl.clear();

        // Populate with unpacked items
        const unpacked = this.getUnpackedItems();
        unpacked.forEach(item => {
            const remaining = (item.quantity_picked || 0) - item.packed;
            itemsControl.push(this.fb.group({
                sale_item_id: [item.id],
                product_name: [item.product?.name],
                product_sku: [item.product?.sku],
                max_quantity: [remaining],
                quantity: [remaining, [Validators.min(0), Validators.max(remaining)]] // Default to all
            }));
        });

        this.modalService.open(content, { size: 'lg' });
    }

    onSubmitPackage() {
        const formVal = this.packageForm.value;

        // Filter items with quantity > 0
        const selectedItems = formVal.items.filter((i: any) => i.quantity > 0).map((i: any) => ({
            sale_item_id: i.sale_item_id,
            quantity: i.quantity
        }));

        if (selectedItems.length === 0) {
            Swal.fire('Atención', 'Debes seleccionar al menos un producto para empacar', 'warning');
            return;
        }

        const payload = {
            sale_id: this.saleId!,
            package_type_id: formVal.package_type_id,
            tracking_number: formVal.tracking_number,
            weight: formVal.weight,
            items: selectedItems
        };

        this.logisticsService.createPackage(payload).subscribe({
            next: (pkg) => {
                this.packages.push(pkg);
                this.modalService.dismissAll();
                this.cdr.detectChanges();
                Swal.fire('Éxito', 'Paquete creado', 'success');
            },
            error: (err) => {
                Swal.fire('Error', 'No se pudo crear el paquete', 'error');
                this.cdr.detectChanges();
            }
        });
    }

    finishPacking() {
        const unpacked = this.getUnpackedItems();
        let message = '¿Marcar como Despachado (Enviado)?';

        if (unpacked.length > 0) {
            message = 'Aún quedan productos sin empacar. ¿Deseas despachar igual?';
        }

        Swal.fire({
            title: 'Finalizar Empaque',
            text: message,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, despachar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.saleService.updateStatus(this.saleId!, 'DISPATCHED').subscribe({
                    next: () => {
                        this.cdr.detectChanges();
                        Swal.fire('Éxito', 'Orden Despachada', 'success').then(() => {
                            this.router.navigate(['/sales/view', this.saleId]);
                        });
                    },
                    error: (err) => {
                        this.cdr.detectChanges();
                        Swal.fire('Error', 'No se pudo actualizar estado', 'error');
                    }
                });
            }
        });
    }
}

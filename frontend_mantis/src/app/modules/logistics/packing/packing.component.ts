import { ChangeDetectorRef, Component, OnInit, TemplateRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormArray, FormBuilder, FormControl, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbModal, NgbNavModule } from '@ng-bootstrap/ng-bootstrap';
import Swal from 'sweetalert2';
import { Sale, SaleItem, SaleService } from '../../../core/services/sale.service';
import { CreatePackageRequest, LogisticsService, PackageType, SalePackage } from '../logistics.service';

interface UnpackedSaleItem extends SaleItem {
    id: string;
    packed: number;
}

interface PackageItemFormValue {
    sale_item_id: string;
    product_name: string;
    product_sku: string;
    max_quantity: number;
    quantity: number;
}

type PackageItemFormGroup = FormGroup<{
    sale_item_id: FormControl<string>;
    product_name: FormControl<string>;
    product_sku: FormControl<string>;
    max_quantity: FormControl<number>;
    quantity: FormControl<number>;
}>;

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
    packageForm: FormGroup;

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
            items: this.fb.array<PackageItemFormGroup>([])
        });
    }

    ngOnInit() {
        this.saleId = this.route.snapshot.paramMap.get('id');
        if (this.saleId) this.loadData();
    }

    loadData() {
        if (!this.saleId) return;
        this.loading = true;

        this.saleService.getSale(this.saleId).subscribe((sale) => {
            this.sale = sale;
            this.cdr.detectChanges();
        });

        this.logisticsService.getPackageTypes().subscribe((types) => {
            this.packageTypes = types;
            this.cdr.detectChanges();
        });

        this.logisticsService.getPackages(this.saleId).subscribe({
            next: (packages) => {
                this.packages = packages;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    getUnpackedItems(): UnpackedSaleItem[] {
        if (!this.sale?.items) return [];
        const items: UnpackedSaleItem[] = this.sale.items
            .filter((item): item is SaleItem & { id: string } => !!item.id)
            .map((item) => ({ ...item, id: item.id, packed: 0 }));

        this.packages.forEach((pkg) => {
            pkg.items.forEach((packageItem) => {
                const item = items.find((i) => i.id === packageItem.sale_item_id);
                if (item) item.packed += packageItem.quantity;
            });
        });

        return items.filter((item) => (item.quantity_picked || 0) - item.packed > 0);
    }

    get itemsFormArray(): FormArray<PackageItemFormGroup> {
        return this.packageForm.get('items') as FormArray<PackageItemFormGroup>;
    }

    createPackage(content: TemplateRef<unknown>) {
        this.packageForm.reset();
        this.itemsFormArray.clear();

        const unpacked = this.getUnpackedItems();
        unpacked.forEach((item) => {
            const remaining = (item.quantity_picked || 0) - item.packed;
            this.itemsFormArray.push(
                this.fb.group({
                    sale_item_id: this.fb.nonNullable.control(item.id),
                    product_name: this.fb.nonNullable.control(item.product?.name || 'Producto'),
                    product_sku: this.fb.nonNullable.control(item.product?.sku || ''),
                    max_quantity: this.fb.nonNullable.control(remaining),
                    quantity: this.fb.nonNullable.control(remaining, [Validators.min(0), Validators.max(remaining)])
                })
            );
        });

        this.modalService.open(content, { size: 'lg' });
    }

    onSubmitPackage() {
        if (!this.saleId) return;
        const formVal = this.packageForm.value as {
            package_type_id: string | null;
            tracking_number: string;
            weight: number;
            items: PackageItemFormValue[];
        };

        const selectedItems = (formVal.items || [])
            .filter((item) => item.quantity > 0)
            .map((item) => ({
                sale_item_id: item.sale_item_id,
                quantity: item.quantity
            }));

        if (selectedItems.length === 0) {
            Swal.fire('Atencion', 'Debes seleccionar al menos un producto para empacar', 'warning');
            return;
        }

        const payload: CreatePackageRequest = {
            sale_id: this.saleId,
            package_type_id: formVal.package_type_id || undefined,
            tracking_number: formVal.tracking_number || undefined,
            weight: Number(formVal.weight || 0),
            items: selectedItems
        };

        this.logisticsService.createPackage(payload).subscribe({
            next: (pkg) => {
                this.packages.push(pkg);
                this.modalService.dismissAll();
                this.cdr.detectChanges();
                Swal.fire('Exito', 'Paquete creado', 'success');
            },
            error: () => {
                Swal.fire('Error', 'No se pudo crear el paquete', 'error');
                this.cdr.detectChanges();
            }
        });
    }

    finishPacking() {
        if (!this.saleId) return;
        const unpacked = this.getUnpackedItems();
        const message =
            unpacked.length > 0 ? 'Aun quedan productos sin empacar. Deseas despachar igual?' : 'Marcar como despachado?';

        Swal.fire({
            title: 'Finalizar Empaque',
            text: message,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Si, despachar'
        }).then((result) => {
            if (!result.isConfirmed) return;
            this.saleService.updateStatus(this.saleId as string, 'DISPATCHED').subscribe({
                next: () => {
                    this.cdr.detectChanges();
                    Swal.fire('Exito', 'Orden despachada', 'success').then(() => {
                        this.router.navigate(['/sales/view', this.saleId]);
                    });
                },
                error: () => {
                    this.cdr.detectChanges();
                    Swal.fire('Error', 'No se pudo actualizar estado', 'error');
                }
            });
        });
    }
}

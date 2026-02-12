import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { InventoryService, InventoryItem } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { ApiService } from '../../../core/services/api.service';

@Component({
    selector: 'app-inventory-list',
    standalone: false,
    templateUrl: './inventory-list.component.html',
    styleUrls: ['./inventory-list.component.scss']
})
export class InventoryListComponent implements OnInit {
    inventoryItems: InventoryItem[] = [];
    branches: any[] = [];
    selectedBranchId: string = '';
    isLoading = false;

    constructor(
        private inventoryService: InventoryService,
        private api: ApiService,
        private cdr: ChangeDetectorRef,
        private swal: SweetAlertService
    ) { }

    ngOnInit(): void {
        this.loadBranches();
        this.loadInventory();
    }

    loadBranches() {
        this.api.get<any[]>('/branches').subscribe({
            next: (data) => {
                this.branches = data;
                this.cdr.detectChanges();
            },
            error: (err) => console.error('Error loading branches', err)
        });
    }

    onBranchChange() {
        this.loadInventory();
    }

    loadInventory() {
        this.isLoading = true;
        this.inventoryService.getInventory(this.selectedBranchId || undefined).subscribe({
            next: (data) => {
                this.inventoryItems = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Error loading inventory', err);
                this.swal.error('Error', 'No se pudo cargar el inventario.');
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }
}

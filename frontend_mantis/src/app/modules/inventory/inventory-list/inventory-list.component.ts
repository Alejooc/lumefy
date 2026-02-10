import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { InventoryService, InventoryItem } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';

@Component({
    selector: 'app-inventory-list',
    standalone: false,
    templateUrl: './inventory-list.component.html',
    styleUrls: ['./inventory-list.component.scss']
})
export class InventoryListComponent implements OnInit {
    inventoryItems: InventoryItem[] = [];
    isLoading = false;

    constructor(
        private inventoryService: InventoryService,
        private cdr: ChangeDetectorRef,
        private swal: SweetAlertService
    ) { }

    ngOnInit(): void {
        this.loadInventory();
    }

    loadInventory() {
        this.isLoading = true;
        this.inventoryService.getInventory().subscribe({
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

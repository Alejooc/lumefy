import { Component, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { InventoryService, InventoryItem } from '../inventory.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { ApiService } from '../../../core/services/api.service';
import { ExportService } from '../../../core/services/export.service';
import { Branch } from 'src/app/core/services/branch.service';

@Component({
    selector: 'app-inventory-list',
    standalone: false,
    templateUrl: './inventory-list.component.html',
    styleUrls: ['./inventory-list.component.scss']
})
export class InventoryListComponent implements OnInit {
    private inventoryService = inject(InventoryService);
    private api = inject(ApiService);
    private cdr = inject(ChangeDetectorRef);
    private swal = inject(SweetAlertService);
    private exportService = inject(ExportService);

    inventoryItems: InventoryItem[] = [];
    branches: Branch[] = [];
    selectedBranchId: string = '';
    isLoading = false;

    ngOnInit(): void {
        this.loadBranches();
        this.loadInventory();
    }

    loadBranches() {
        this.api.get<Branch[]>('/branches').subscribe({
            next: (data) => {
                this.branches = data;
                this.cdr.detectChanges();
            },
            error: (error: unknown) => console.error('Error loading branches', error)
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

    exportData(format: 'excel' | 'csv') {
        const params: Record<string, string> = {};
        if (this.selectedBranchId) params['branch_id'] = this.selectedBranchId;
        this.exportService.download('/inventory/export', format, params);
    }
}

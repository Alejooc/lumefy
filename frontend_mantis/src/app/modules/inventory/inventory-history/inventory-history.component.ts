import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { InventoryService, InventoryMovement } from '../inventory.service';
import { SharedModule } from '../../../theme/shared/shared.module';

@Component({
    selector: 'app-inventory-history',
    templateUrl: './inventory-history.component.html',
    styleUrls: ['./inventory-history.component.scss'],
    standalone: true,
    imports: [CommonModule, SharedModule, RouterModule]
})
export class InventoryHistoryComponent implements OnInit {
    movements: InventoryMovement[] = [];
    isLoading = false;
    productId: string | null = null;
    branchId: string | null = null;

    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private inventoryService: InventoryService
    ) { }

    ngOnInit(): void {
        this.productId = this.route.snapshot.paramMap.get('productId');
        this.branchId = this.route.snapshot.queryParamMap.get('branchId');

        if (this.productId) {
            this.loadHistory();
        }
    }

    loadHistory() {
        this.isLoading = true;
        this.inventoryService.getMovements(this.productId!, this.branchId || undefined).subscribe({
            next: (data) => {
                this.movements = data;
                this.isLoading = false;
            },
            error: (err) => {
                console.error(err);
                this.isLoading = false;
            }
        });
    }

    goBack() {
        this.router.navigate(['/inventory']);
    }
}

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { SaleService, Sale } from '../../../core/services/sale.service';
import { InventoryService } from '../inventory.service';
import { switchMap, forkJoin, map, of } from 'rxjs';

@Component({
    selector: 'app-picking-print',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './picking-print.component.html',
    styles: [`
        @media print {
            .no-print { display: none !important; }
            .print-container { width: 100%; max-width: none; }
            body { background: white; }
        }
        .print-container {
            font-family: 'Inter', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            color: #333;
        }
        h2 { border-bottom: 2px solid #eee; padding-bottom: 10px; margin-bottom: 20px; }
        .meta-info { display: flex; justify-content: space-between; margin-bottom: 30px; }
        .meta-box { width: 48%; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { font-weight: 600; text-transform: uppercase; font-size: 0.85rem; color: #555; }
        .footer { margin-top: 50px; font-size: 0.9rem; border-top: 1px solid #eee; padding-top: 20px; }
        .sign-box { border: 1px solid #ccc; height: 60px; width: 200px; margin-top: 10px; }
    `]
})
export class PickingPrintComponent implements OnInit {
    sale: Sale | null = null;
    itemsWithLocation: any[] = [];
    loading = false;
    currentDate = new Date();

    private route = inject(ActivatedRoute);
    private saleService = inject(SaleService);
    private inventoryService = inject(InventoryService);

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) this.loadData(id);
        });
    }

    loadData(id: string) {
        this.loading = true;
        this.saleService.getSale(id).pipe(
            switchMap(sale => {
                this.sale = sale;
                if (!sale.items || sale.items.length === 0) return of([]);

                // For each item, find inventory location
                const locationRequests = sale.items.map(item =>
                    this.inventoryService.getInventory(sale.branch_id, item.product_id).pipe(
                        map(inv => {
                            // Find inventory record for this branch/product
                            // Assuming getInventory returns list filtering by branch/product
                            // Location might be in the first record found
                            const rec = inv.find(i => i.branch_id === sale.branch_id);
                            return {
                                ...item,
                                location: rec?.location || 'General',
                                stock: rec?.quantity || 0
                            };
                        })
                    )
                );
                return forkJoin(locationRequests);
            })
        ).subscribe({
            next: (items) => {
                this.itemsWithLocation = items;
                this.loading = false;
                // Optional: Auto-print
                // setTimeout(() => window.print(), 1000);
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
            }
        });
    }

    print() {
        window.print();
    }
}

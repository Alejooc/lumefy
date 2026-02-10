import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { PriceListService, PriceList } from '../../../core/services/pricelist.service';

@Component({
    selector: 'app-pricelist-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './pricelist-list.component.html',
    styleUrls: ['./pricelist-list.component.scss']
})
export class PriceListListComponent implements OnInit {
    private priceListService = inject(PriceListService);
    priceLists: PriceList[] = [];
    loading = false;

    ngOnInit() {
        this.loadPriceLists();
    }

    loadPriceLists() {
        this.loading = true;
        this.priceListService.getPriceLists().subscribe({
            next: (data) => {
                this.priceLists = data;
                this.loading = false;
            },
            error: (err) => {
                console.error('Error loading price lists', err);
                this.loading = false;
            }
        });
    }
}

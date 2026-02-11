import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

@Component({
    selector: 'app-company-list',
    standalone: false, // Part of AdminModule
    templateUrl: './company-list.component.html'
})
export class CompanyListComponent implements OnInit {
    companies: any[] = [];
    loading = false;

    private api = inject(ApiService);

    ngOnInit() {
        this.loadCompanies();
    }

    loadCompanies() {
        this.loading = true;
        this.api.get<any[]>('/admin/companies').subscribe({
            next: (data) => {
                this.companies = data;
                this.loading = false;
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
            }
        });
    }
}

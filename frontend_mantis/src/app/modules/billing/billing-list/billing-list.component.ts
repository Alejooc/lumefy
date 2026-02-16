import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';
import { SharedModule } from 'src/app/theme/shared/shared.module';

@Component({
    selector: 'app-billing-list',
    standalone: true,
    imports: [CommonModule, SharedModule, RouterModule],
    templateUrl: './billing-list.component.html',
    styleUrls: ['./billing-list.component.scss']
})
export class BillingListComponent {
    authService = inject(AuthService);
    user$ = this.authService.currentUser;

    // Mock data for payments history
    payments = [
        { date: '2024-02-01', amount: 49.00, status: 'PAID', invoice: 'INV-001' },
        { date: '2024-01-01', amount: 49.00, status: 'PAID', invoice: 'INV-000' }
    ];
}

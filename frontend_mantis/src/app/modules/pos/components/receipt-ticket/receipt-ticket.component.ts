import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { POSCartItem } from 'src/app/core/services/pos.service';

interface ReceiptSale {
    id: string;
    total: number;
    change: number;
    items: POSCartItem[];
    payment_method: string;
    amount_paid: number | null;
    date: Date;
}

interface ReceiptCompany {
    name?: string;
    nif?: string;
    address?: string;
}

@Component({
    selector: 'app-receipt-ticket',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './receipt-ticket.component.html',
    styleUrls: ['./receipt-ticket.component.scss']
})
export class ReceiptTicketComponent {
    @Input() sale: ReceiptSale | null = null;
    @Input() company: ReceiptCompany | null = null;
}

import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-receipt-ticket',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './receipt-ticket.component.html',
    styleUrls: ['./receipt-ticket.component.scss']
})
export class ReceiptTicketComponent {
    @Input() sale: any = null;
    @Input() company: any = null;
}

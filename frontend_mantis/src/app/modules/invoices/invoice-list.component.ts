import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';

import { Invoice, InvoiceService, InvoiceStatus, InvoiceType } from '../../core/services/invoice.service';
import { SkeletonComponent } from '../../theme/shared/components/skeleton/skeleton.component';

@Component({
  selector: 'app-invoice-list',
  standalone: true,
  imports: [CommonModule, FormsModule, SkeletonComponent],
  templateUrl: './invoice-list.component.html'
})
export class InvoiceListComponent implements OnInit {
  invoices: Invoice[] = [];
  loading = false;
  filterType = '';
  filterStatus = '';
  sourceType: InvoiceType = 'SALE';
  sourceId = '';
  dueDate = '';

  private readonly invoiceService = inject(InvoiceService);
  private readonly cdr = inject(ChangeDetectorRef);

  ngOnInit(): void {
    this.loadInvoices();
  }

  loadInvoices(): void {
    this.loading = true;
    this.invoiceService.list(
      this.filterType ? this.filterType as InvoiceType : undefined,
      this.filterStatus ? this.filterStatus as InvoiceStatus : undefined
    ).subscribe({
      next: (invoices) => {
        this.invoices = invoices;
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => this.handleError(error)
    });
  }

  createFromSource(): void {
    if (!this.sourceId.trim()) {
      Swal.fire('Falta el documento', 'Indica el ID de la venta u orden de compra.', 'warning');
      return;
    }
    const payload = this.sourceType === 'SALE'
      ? { type: 'SALE' as const, sale_id: this.sourceId.trim(), due_date: this.dueDate || undefined }
      : { type: 'PURCHASE' as const, purchase_id: this.sourceId.trim(), due_date: this.dueDate || undefined };
    this.loading = true;
    this.invoiceService.createFromSource(payload).subscribe({
      next: (invoice) => {
        this.sourceId = '';
        this.dueDate = '';
        this.loading = false;
        this.loadInvoices();
        Swal.fire('Factura creada', `${invoice.number} quedó en borrador.`, 'success');
      },
      error: (error) => this.handleError(error)
    });
  }

  post(invoice: Invoice): void {
    Swal.fire({
      title: `¿Contabilizar ${invoice.number}?`,
      text: 'Esto generará la cuenta por cobrar o por pagar.',
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Contabilizar',
      cancelButtonText: 'Cancelar'
    }).then((result) => {
      if (!result.isConfirmed) return;
      this.loading = true;
      this.invoiceService.post(invoice.id).subscribe({
        next: () => { this.loadInvoices(); Swal.fire('Contabilizada', 'La factura ya afecta cartera.', 'success'); },
        error: (error) => this.handleError(error)
      });
    });
  }

  pay(invoice: Invoice): void {
    const pending = invoice.total - invoice.amount_paid;
    Swal.fire({
      title: `Registrar pago · ${invoice.number}`,
      html: `<input id="paymentAmount" class="swal2-input" type="number" min="0.01" step="0.01" value="${pending}">
             <select id="paymentMethod" class="swal2-select"><option value="CASH">Efectivo</option><option value="CARD">Tarjeta</option><option value="TRANSFER">Transferencia</option></select>
             <input id="paymentReference" class="swal2-input" placeholder="Referencia (opcional)">`,
      showCancelButton: true,
      confirmButtonText: 'Registrar pago',
      preConfirm: () => {
        const amount = Number((document.getElementById('paymentAmount') as HTMLInputElement).value);
        const method = (document.getElementById('paymentMethod') as HTMLSelectElement).value;
        const reference = (document.getElementById('paymentReference') as HTMLInputElement).value;
        if (!Number.isFinite(amount) || amount <= 0 || amount > pending) {
          Swal.showValidationMessage(`El pago debe estar entre 0.01 y ${pending.toFixed(2)}`);
          return undefined;
        }
        return { amount, method, reference: reference || undefined };
      }
    }).then((result) => {
      if (!result.isConfirmed || !result.value) return;
      this.loading = true;
      this.invoiceService.registerPayment(invoice.id, result.value).subscribe({
        next: () => { this.loadInvoices(); Swal.fire('Pago registrado', 'El saldo de la factura fue actualizado.', 'success'); },
        error: (error) => this.handleError(error)
      });
    });
  }

  cancel(invoice: Invoice): void {
    Swal.fire({ title: `¿Cancelar ${invoice.number}?`, text: 'Solo se puede cancelar un borrador.', icon: 'warning', showCancelButton: true }).then((result) => {
      if (!result.isConfirmed) return;
      this.loading = true;
      this.invoiceService.cancel(invoice.id).subscribe({
        next: () => { this.loadInvoices(); Swal.fire('Factura cancelada', '', 'success'); },
        error: (error) => this.handleError(error)
      });
    });
  }

  statusClass(status: InvoiceStatus): string {
    return ({ DRAFT: 'bg-secondary', POSTED: 'bg-primary', PARTIALLY_PAID: 'bg-warning text-dark', PAID: 'bg-success', CANCELLED: 'bg-danger' } as Record<InvoiceStatus, string>)[status];
  }

  private handleError(error: any): void {
    this.loading = false;
    this.cdr.detectChanges();
    Swal.fire('No se pudo completar la operación', error?.error?.detail || 'Intenta de nuevo.', 'error');
  }
}

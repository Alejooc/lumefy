import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import Swal from 'sweetalert2';

import { Branch, BranchService } from '../../../core/services/branch.service';
import { Product, ProductService } from '../../../core/services/product.service';
import { ProcurementService, PurchaseRequest } from '../../../core/services/procurement.service';
import { Supplier, SupplierService } from '../../../core/services/supplier.service';

@Component({
  selector: 'app-purchase-requests',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './purchase-requests.component.html'
})
export class PurchaseRequestsComponent implements OnInit {
  requests: PurchaseRequest[] = [];
  branches: Branch[] = [];
  products: Product[] = [];
  suppliers: Supplier[] = [];
  loading = false;
  showForm = false;
  quoteRequestId: string | null = null;
  quoteSupplierId = '';
  quoteReference = '';
  quoteCosts: Record<string, number> = {};
  form = { branch_id: '', priority: 'NORMAL', notes: '', items: [{ product_id: '', quantity: 1 }] };

  private readonly procurement = inject(ProcurementService);
  private readonly branchesService = inject(BranchService);
  private readonly productsService = inject(ProductService);
  private readonly suppliersService = inject(SupplierService);
  private readonly cdr = inject(ChangeDetectorRef);

  ngOnInit(): void { this.load(); }

  load(): void {
    this.loading = true;
    forkJoin({
      requests: this.procurement.listRequests(),
      branches: this.branchesService.getBranches(),
      products: this.productsService.getProducts(),
      suppliers: this.suppliersService.getSuppliers()
    }).subscribe({
      next: ({ requests, branches, products, suppliers }) => {
        this.requests = requests;
        this.branches = branches;
        this.products = products.filter(product => product.purchase_ok !== false);
        this.suppliers = suppliers;
        this.loading = false;
        this.cdr.detectChanges();
      }, error: (error) => this.error(error)
    });
  }

  addLine(): void { this.form.items.push({ product_id: '', quantity: 1 }); }
  removeLine(index: number): void { this.form.items.splice(index, 1); }

  saveRequest(): void {
    const validItems = this.form.items.filter(item => item.product_id && item.quantity > 0);
    if (!this.form.branch_id || validItems.length !== this.form.items.length) {
      Swal.fire('Completa la solicitud', 'Selecciona sucursal, producto y cantidad en cada línea.', 'warning');
      return;
    }
    this.loading = true;
    this.procurement.createRequest({ ...this.form, items: validItems }).subscribe({
      next: () => {
        this.form = { branch_id: '', priority: 'NORMAL', notes: '', items: [{ product_id: '', quantity: 1 }] };
        this.showForm = false;
        this.load();
        Swal.fire('Solicitud creada', 'Envíala a aprobación para empezar a cotizar.', 'success');
      }, error: (error) => this.error(error)
    });
  }

  changeStatus(request: PurchaseRequest, status: 'SUBMITTED' | 'APPROVED' | 'CANCELLED'): void {
    this.loading = true;
    this.procurement.updateRequestStatus(request.id, status).subscribe({
      next: () => { this.load(); }, error: (error) => this.error(error)
    });
  }

  beginQuote(request: PurchaseRequest): void {
    this.quoteRequestId = request.id;
    this.quoteSupplierId = '';
    this.quoteReference = '';
    this.quoteCosts = Object.fromEntries(request.items.map(item => [item.product_id, 0]));
  }

  saveQuote(request: PurchaseRequest): void {
    if (!this.quoteSupplierId || request.items.some(item => this.quoteCosts[item.product_id] === undefined || this.quoteCosts[item.product_id] < 0)) {
      Swal.fire('Completa la cotización', 'Selecciona proveedor e indica un costo válido para cada producto.', 'warning');
      return;
    }
    this.loading = true;
    this.procurement.createQuote(request.id, {
      supplier_id: this.quoteSupplierId,
      reference_number: this.quoteReference || undefined,
      items: request.items.map(item => ({ product_id: item.product_id, quantity: item.quantity, unit_cost: Number(this.quoteCosts[item.product_id]) }))
    }).subscribe({
      next: () => { this.quoteRequestId = null; this.load(); Swal.fire('Cotización registrada', 'Ya puedes compararla y elegir la mejor opción.', 'success'); },
      error: (error) => this.error(error)
    });
  }

  acceptQuote(quoteId: string): void {
    Swal.fire({ title: '¿Seleccionar esta cotización?', text: 'Se creará una orden de compra en borrador.', icon: 'question', showCancelButton: true, confirmButtonText: 'Crear orden' }).then(result => {
      if (!result.isConfirmed) return;
      this.loading = true;
      this.procurement.acceptQuote(quoteId).subscribe({
        next: ({ purchase_id }) => { this.load(); Swal.fire('Orden creada', `La orden ${purchase_id.slice(0, 8)} ya está lista para validación.`, 'success'); },
        error: (error) => this.error(error)
      });
    });
  }

  productName(productId: string): string { return this.products.find(product => product.id === productId)?.name || productId; }
  supplierName(supplierId: string): string { return this.suppliers.find(supplier => supplier.id === supplierId)?.name || supplierId; }

  private error(error: any): void {
    this.loading = false;
    this.cdr.detectChanges();
    Swal.fire('No se pudo completar la operación', error?.error?.detail || 'Intenta de nuevo.', 'error');
  }
}

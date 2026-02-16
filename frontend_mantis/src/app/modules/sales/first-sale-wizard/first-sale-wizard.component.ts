import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import Swal from 'sweetalert2';
import { ApiService } from '../../../core/services/api.service';
import { PermissionService } from '../../../core/services/permission.service';

type Branch = { id: string; name: string };
type Product = { id: string; name: string; price: number; cost?: number };
type Client = { id: string; name: string };
type Sale = { id: string; total: number; status: string };

@Component({
  selector: 'app-first-sale-wizard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './first-sale-wizard.component.html',
  styleUrl: './first-sale-wizard.component.scss'
})
export class FirstSaleWizardComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private permissionService = inject(PermissionService);

  loading = false;
  creatingProduct = false;
  creatingClient = false;
  creatingSale = false;
  currentStep = 1;

  branches: Branch[] = [];
  products: Product[] = [];
  clients: Client[] = [];

  createdProductId: string | null = null;
  createdClientId: string | null = null;
  createdSale: Sale | null = null;

  canCreateProduct = this.permissionService.hasPermission('manage_inventory');
  canCreateClient = this.permissionService.hasPermission('manage_clients');
  canCreateSale = this.permissionService.hasPermission('create_sales');
  canViewProducts = this.permissionService.hasPermission('view_products');

  productForm = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(120)]],
    price: [0, [Validators.required, Validators.min(0.01)]],
    cost: [0, [Validators.min(0)]],
    sku: [''],
    track_inventory: [true]
  });

  clientForm = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(120)]],
    email: ['', [Validators.email]],
    phone: [''],
    address: ['']
  });

  saleForm = this.fb.group({
    branch_id: ['', [Validators.required]],
    product_id: ['', [Validators.required]],
    quantity: [1, [Validators.required, Validators.min(0.01)]],
    client_id: [''],
    notes: ['Primera venta desde wizard MVP']
  });

  ngOnInit(): void {
    this.loadDependencies();
  }

  loadDependencies(): void {
    this.loading = true;
    forkJoin({
      branches: this.api.get<Branch[]>('/branches').pipe(catchError(() => of([] as Branch[]))),
      products: this.api.get<Product[]>('/products').pipe(catchError(() => of([] as Product[]))),
      clients: this.api.get<Client[]>('/clients').pipe(catchError(() => of([] as Client[])))
    }).subscribe({
      next: ({ branches, products, clients }) => {
        this.branches = branches;
        this.products = products;
        this.clients = clients;

        if (this.branches.length === 1) {
          this.saleForm.patchValue({ branch_id: this.branches[0].id });
        }

        if (this.products.length > 0) {
          this.saleForm.patchValue({ product_id: this.products[0].id });
        }

        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  createQuickProduct(): void {
    if (!this.canCreateProduct) {
      Swal.fire('Sin permiso', 'No tienes permiso para crear productos.', 'warning');
      return;
    }

    if (this.productForm.invalid) {
      this.productForm.markAllAsTouched();
      return;
    }

    this.creatingProduct = true;
    const payload = {
      ...this.productForm.getRawValue(),
      product_type: 'STORABLE',
      tax_rate: 0,
      min_stock: 0,
      sale_ok: true,
      purchase_ok: true,
      images: []
    };

    this.api.post<Product>('/products', payload).subscribe({
      next: (created) => {
        this.creatingProduct = false;
        this.products = [created, ...this.products];
        this.createdProductId = created.id;
        this.saleForm.patchValue({ product_id: created.id });
        this.currentStep = 2;
        Swal.fire('Producto creado', 'Paso 1 completado.', 'success');
      },
      error: (err) => {
        this.creatingProduct = false;
        Swal.fire('Error', err?.error?.detail || 'No se pudo crear el producto.', 'error');
      }
    });
  }

  skipClientStep(): void {
    this.currentStep = 3;
  }

  createQuickClient(): void {
    if (!this.canCreateClient) {
      Swal.fire('Sin permiso', 'No tienes permiso para crear clientes.', 'warning');
      return;
    }

    if (this.clientForm.invalid) {
      this.clientForm.markAllAsTouched();
      return;
    }

    this.creatingClient = true;
    this.api.post<Client>('/clients', this.clientForm.getRawValue()).subscribe({
      next: (created) => {
        this.creatingClient = false;
        this.clients = [created, ...this.clients];
        this.createdClientId = created.id;
        this.saleForm.patchValue({ client_id: created.id });
        this.currentStep = 3;
        Swal.fire('Cliente creado', 'Paso 2 completado.', 'success');
      },
      error: (err) => {
        this.creatingClient = false;
        Swal.fire('Error', err?.error?.detail || 'No se pudo crear el cliente.', 'error');
      }
    });
  }

  createFirstSale(): void {
    if (!this.canCreateSale) {
      Swal.fire('Sin permiso', 'No tienes permiso para crear ventas.', 'warning');
      return;
    }

    if (this.saleForm.invalid) {
      this.saleForm.markAllAsTouched();
      return;
    }

    const form = this.saleForm.getRawValue();
    const selectedProduct = this.products.find((p) => p.id === form.product_id);
    if (!selectedProduct) {
      Swal.fire('Producto requerido', 'Selecciona un producto valido para continuar.', 'warning');
      return;
    }

    this.creatingSale = true;
    const payload = {
      branch_id: form.branch_id,
      client_id: form.client_id || null,
      status: 'CONFIRMED',
      payment_method: 'CASH',
      notes: form.notes || null,
      items: [
        {
          product_id: form.product_id,
          quantity: Number(form.quantity),
          price: Number(selectedProduct.price || 0),
          discount: 0
        }
      ],
      payments: []
    };

    this.api.post<Sale>('/sales', payload).subscribe({
      next: (created) => {
        this.creatingSale = false;
        this.createdSale = created;
        Swal.fire('Primera venta creada', 'Flujo MVP completado con exito.', 'success');
      },
      error: (err) => {
        this.creatingSale = false;
        Swal.fire('Error', err?.error?.detail || 'No se pudo crear la venta.', 'error');
      }
    });
  }

  get selectedProductPrice(): number {
    const productId = this.saleForm.get('product_id')?.value || '';
    const product = this.products.find((item) => item.id === productId);
    return Number(product?.price || 0);
  }

  get estimatedTotal(): number {
    const qty = Number(this.saleForm.get('quantity')?.value || 0);
    return qty * this.selectedProductPrice;
  }
}


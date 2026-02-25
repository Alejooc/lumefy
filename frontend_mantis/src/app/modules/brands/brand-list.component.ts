import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';
import { ApiService } from '../../core/services/api.service';

export interface Brand {
    id?: string;
    name: string;
    description?: string;
}

@Component({
    selector: 'app-brand-list',
    standalone: true,
    imports: [FormsModule],
    template: `
    <div class="row">
      <div class="col-sm-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5>Marcas</h5>
          </div>
          <div class="card-body">
            <!-- Add Form -->
            <div class="row mb-4">
              <div class="col-md-4">
                <input type="text" class="form-control" [(ngModel)]="newBrand.name"
                  placeholder="Nombre de marca" (keyup.enter)="saveBrand()">
                </div>
                <div class="col-md-5">
                  <input type="text" class="form-control" [(ngModel)]="newBrand.description"
                    placeholder="Descripción (opcional)" (keyup.enter)="saveBrand()">
                  </div>
                  <div class="col-md-3">
                    <button class="btn btn-primary w-100" (click)="saveBrand()" [disabled]="!newBrand.name || loading">
                      {{ editingId ? 'Actualizar' : 'Crear Marca' }}
                    </button>
                    @if (editingId) {
                      <button class="btn btn-secondary btn-sm w-100 mt-1" (click)="cancelEdit()">Cancelar</button>
                    }
                  </div>
                </div>
    
                <!-- Loading -->
                @if (loading) {
                  <div class="text-center py-3">
                    <div class="spinner-border spinner-border-sm text-primary"></div>
                  </div>
                }
    
                <!-- Table -->
                @if (!loading) {
                  <div class="table-responsive">
                    <table class="table table-hover">
                      <thead>
                        <tr>
                          <th>Nombre</th>
                          <th>Descripción</th>
                          <th style="width: 120px;">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (brand of brands; track brand) {
                          <tr>
                            <td class="fw-bold">{{ brand.name }}</td>
                            <td class="text-muted">{{ brand.description || '—' }}</td>
                            <td>
                              <button class="btn btn-outline-primary btn-sm me-1" (click)="editBrand(brand)" title="Editar">
                                <i class="feather icon-edit"></i>
                              </button>
                              <button class="btn btn-outline-danger btn-sm" (click)="deleteBrand(brand)" title="Eliminar">
                                <i class="feather icon-trash-2"></i>
                              </button>
                            </td>
                          </tr>
                        }
                        @if (brands.length === 0) {
                          <tr>
                            <td colspan="3" class="text-center text-muted py-3">No hay marcas registradas.</td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>
    `
})
export class BrandListComponent implements OnInit {
    brands: Brand[] = [];
    newBrand: Brand = { name: '', description: '' };
    editingId: string | null = null;
    loading = false;

    private api = inject(ApiService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadBrands();
    }

    loadBrands() {
        this.loading = true;
        this.api.get<Brand[]>('/brands').subscribe({
            next: (data) => { this.brands = data; this.loading = false; this.cdr.detectChanges(); },
            error: () => { this.loading = false; this.cdr.detectChanges(); }
        });
    }

    saveBrand() {
        if (!this.newBrand.name) return;

        const request = this.editingId
            ? this.api.put(`/brands/${this.editingId}`, this.newBrand)
            : this.api.post('/brands', this.newBrand);

        request.subscribe({
            next: () => {
                Swal.fire('Éxito', this.editingId ? 'Marca actualizada' : 'Marca creada', 'success');
                this.newBrand = { name: '', description: '' };
                this.editingId = null;
                this.loadBrands();
            },
            error: (err: { error?: { detail?: string } }) => {
                Swal.fire('Error', err.error?.detail || 'No se pudo guardar', 'error');
            }
        });
    }

    editBrand(brand: Brand) {
        this.editingId = brand.id!;
        this.newBrand = { name: brand.name, description: brand.description || '' };
    }

    cancelEdit() {
        this.editingId = null;
        this.newBrand = { name: '', description: '' };
    }

    deleteBrand(brand: Brand) {
        Swal.fire({
            title: '¿Eliminar marca?',
            text: `Se eliminará "${brand.name}". Esta acción no se puede deshacer.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.api.delete(`/brands/${brand.id}`).subscribe({
                    next: () => {
                        Swal.fire('Eliminada', 'Marca eliminada correctamente', 'success');
                        this.loadBrands();
                    },
                    error: (err: { error?: { detail?: string } }) => {
                        Swal.fire('Error', err.error?.detail || 'No se pudo eliminar', 'error');
                    }
                });
            }
        });
    }
}


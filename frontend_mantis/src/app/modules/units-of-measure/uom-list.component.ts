import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';

import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';
import { ApiService } from '../../core/services/api.service';

export interface UnitOfMeasure {
    id?: string;
    name: string;
    abbreviation?: string;
}

@Component({
    selector: 'app-uom-list',
    standalone: true,
    imports: [FormsModule],
    template: `
    <div class="row">
      <div class="col-sm-12">
        <div class="card">
          <div class="card-header d-flex justify-content-between align-items-center">
            <h5>Unidades de Medida</h5>
          </div>
          <div class="card-body">
            <!-- Add Form -->
            <div class="row mb-4">
              <div class="col-md-4">
                <input type="text" class="form-control" [(ngModel)]="newUom.name"
                  placeholder="Nombre (ej. Kilogramo)" (keyup.enter)="saveUom()">
                </div>
                <div class="col-md-3">
                  <input type="text" class="form-control" [(ngModel)]="newUom.abbreviation"
                    placeholder="Abreviación (ej. kg)" (keyup.enter)="saveUom()">
                  </div>
                  <div class="col-md-3">
                    <button class="btn btn-primary w-100" (click)="saveUom()" [disabled]="!newUom.name || loading">
                      {{ editingId ? 'Actualizar' : 'Crear Unidad' }}
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
                          <th>Abreviación</th>
                          <th style="width: 120px;">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (uom of units; track uom) {
                          <tr>
                            <td class="fw-bold">{{ uom.name }}</td>
                            <td><span class="badge bg-light text-dark">{{ uom.abbreviation || '—' }}</span></td>
                            <td>
                              <button class="btn btn-outline-primary btn-sm me-1" (click)="editUom(uom)" title="Editar">
                                <i class="feather icon-edit"></i>
                              </button>
                              <button class="btn btn-outline-danger btn-sm" (click)="deleteUom(uom)" title="Eliminar">
                                <i class="feather icon-trash-2"></i>
                              </button>
                            </td>
                          </tr>
                        }
                        @if (units.length === 0) {
                          <tr>
                            <td colspan="3" class="text-center text-muted py-3">No hay unidades registradas.</td>
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
export class UomListComponent implements OnInit {
    units: UnitOfMeasure[] = [];
    newUom: UnitOfMeasure = { name: '', abbreviation: '' };
    editingId: string | null = null;
    loading = false;

    private api = inject(ApiService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadUnits();
    }

    loadUnits() {
        this.loading = true;
        this.api.get<UnitOfMeasure[]>('/units-of-measure').subscribe({
            next: (data) => { this.units = data; this.loading = false; this.cdr.detectChanges(); },
            error: () => { this.loading = false; this.cdr.detectChanges(); }
        });
    }

    saveUom() {
        if (!this.newUom.name) return;

        const request = this.editingId
            ? this.api.put(`/units-of-measure/${this.editingId}`, this.newUom)
            : this.api.post('/units-of-measure', this.newUom);

        request.subscribe({
            next: () => {
                Swal.fire('Éxito', this.editingId ? 'Unidad actualizada' : 'Unidad creada', 'success');
                this.newUom = { name: '', abbreviation: '' };
                this.editingId = null;
                this.loadUnits();
            },
            error: (err: { error?: { detail?: string } }) => {
                Swal.fire('Error', err.error?.detail || 'No se pudo guardar', 'error');
            }
        });
    }

    editUom(uom: UnitOfMeasure) {
        this.editingId = uom.id!;
        this.newUom = { name: uom.name, abbreviation: uom.abbreviation || '' };
    }

    cancelEdit() {
        this.editingId = null;
        this.newUom = { name: '', abbreviation: '' };
    }

    deleteUom(uom: UnitOfMeasure) {
        Swal.fire({
            title: '¿Eliminar unidad?',
            text: `Se eliminará "${uom.name}". Esta acción no se puede deshacer.`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.api.delete(`/units-of-measure/${uom.id}`).subscribe({
                    next: () => {
                        Swal.fire('Eliminada', 'Unidad eliminada correctamente', 'success');
                        this.loadUnits();
                    },
                    error: (err: { error?: { detail?: string } }) => {
                        Swal.fire('Error', err.error?.detail || 'No se pudo eliminar', 'error');
                    }
                });
            }
        });
    }
}


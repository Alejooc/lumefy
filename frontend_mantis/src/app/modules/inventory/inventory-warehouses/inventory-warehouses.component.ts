import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiService } from 'src/app/core/services/api.service';
import { Branch } from 'src/app/core/services/branch.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

interface Warehouse { id: string; branch_id: string; name: string; code: string; is_default: boolean; allows_ecommerce: boolean; }
interface Location { id: string; warehouse_id?: string | null; name: string; code: string; location_type: string; is_dispatch_location: boolean; }

@Component({
  selector: 'app-inventory-warehouses',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inventory-warehouses.component.html'
})
export class InventoryWarehousesComponent implements OnInit {
  private api = inject(ApiService);
  private swal = inject(SweetAlertService);

  branches: Branch[] = [];
  warehouses: Warehouse[] = [];
  locations: Location[] = [];
  selectedWarehouseId = '';
  loading = false;
  saving = false;
  showWarehouseModal = false;
  showLocationModal = false;
  warehouseForm = this.newWarehouseForm();
  locationForm = this.newLocationForm();

  ngOnInit(): void { this.load(); }

  get selectedWarehouse(): Warehouse | null { return this.warehouses.find((item) => item.id === this.selectedWarehouseId) || null; }
  branchName(branchId: string): string { return this.branches.find((item) => item.id === branchId)?.name || 'Sucursal'; }

  load(): void {
    this.loading = true;
    this.api.get<Branch[]>('/branches').subscribe({ next: (branches) => {
      this.branches = branches;
      this.api.get<Warehouse[]>('/warehouses/').subscribe({ next: (warehouses) => {
        this.warehouses = warehouses;
        this.selectedWarehouseId = this.selectedWarehouseId || warehouses[0]?.id || '';
        this.loadLocations();
      }, error: () => this.finishLoading('No se pudieron cargar las bodegas.') });
    }, error: () => this.finishLoading('No se pudieron cargar las sucursales.') });
  }

  loadLocations(): void {
    if (!this.selectedWarehouseId) { this.locations = []; this.loading = false; return; }
    this.api.get<Location[]>('/inventory/locations/', { warehouse_id: this.selectedWarehouseId }).subscribe({
      next: (locations) => { this.locations = locations; this.loading = false; },
      error: () => this.finishLoading('No se pudieron cargar las ubicaciones.')
    });
  }

  openWarehouseModal(): void { this.warehouseForm = this.newWarehouseForm(); this.showWarehouseModal = true; }
  openLocationModal(): void {
    if (!this.selectedWarehouse) return;
    this.locationForm = this.newLocationForm();
    this.showLocationModal = true;
  }

  saveWarehouse(): void {
    if (!this.warehouseForm.branch_id || !this.warehouseForm.name.trim() || !this.warehouseForm.code.trim()) return;
    this.saving = true;
    this.api.post<Warehouse>('/warehouses/', { ...this.warehouseForm, name: this.warehouseForm.name.trim(), code: this.warehouseForm.code.trim() }).subscribe({
      next: (warehouse) => { this.showWarehouseModal = false; this.selectedWarehouseId = warehouse.id; this.saving = false; this.swal.success('Bodega creada'); this.load(); },
      error: (err) => { this.saving = false; this.swal.error('Error', err?.error?.detail || 'No se pudo crear la bodega.'); }
    });
  }

  saveLocation(): void {
    const warehouse = this.selectedWarehouse;
    if (!warehouse || !this.locationForm.name.trim() || !this.locationForm.code.trim()) return;
    this.saving = true;
    this.api.post<Location>('/inventory/locations/', { ...this.locationForm, branch_id: warehouse.branch_id, warehouse_id: warehouse.id, name: this.locationForm.name.trim(), code: this.locationForm.code.trim() }).subscribe({
      next: () => { this.showLocationModal = false; this.saving = false; this.swal.success('Ubicación creada'); this.loadLocations(); },
      error: (err) => { this.saving = false; this.swal.error('Error', err?.error?.detail || 'No se pudo crear la ubicación.'); }
    });
  }

  private finishLoading(message: string): void { this.loading = false; this.swal.error('Error', message); }
  private newWarehouseForm() { return { branch_id: this.branches[0]?.id || '', name: '', code: '', is_default: false, allows_ecommerce: true }; }
  private newLocationForm() { return { name: '', code: '', location_type: 'STORAGE', is_dispatch_location: false }; }
}

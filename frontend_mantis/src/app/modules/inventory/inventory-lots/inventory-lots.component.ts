import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { Branch, BranchService } from '../../../core/services/branch.service';
import { InventoryLot, InventoryService } from '../inventory.service';

@Component({
  selector: 'app-inventory-lots',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './inventory-lots.component.html'
})
export class InventoryLotsComponent implements OnInit {
  lots: InventoryLot[] = [];
  branches: Branch[] = [];
  selectedBranchId = '';
  search = '';
  loading = false;

  private readonly inventory = inject(InventoryService);
  private readonly branchService = inject(BranchService);
  private readonly cdr = inject(ChangeDetectorRef);

  ngOnInit(): void {
    this.branchService.getBranches().subscribe({ next: branches => { this.branches = branches; this.cdr.detectChanges(); } });
    this.loadLots();
  }

  loadLots(): void {
    this.loading = true;
    this.inventory.getLots(this.selectedBranchId || undefined).subscribe({
      next: lots => { this.lots = lots; this.loading = false; this.cdr.detectChanges(); },
      error: () => { this.loading = false; this.cdr.detectChanges(); }
    });
  }

  get filteredLots(): InventoryLot[] {
    const term = this.search.trim().toLowerCase();
    if (!term) return this.lots;
    return this.lots.filter(lot => [lot.product_name, lot.lot_number, lot.serial_number, lot.branch_name].some(value => value?.toLowerCase().includes(term)));
  }

  expiryClass(expiryDate?: string): string {
    if (!expiryDate) return '';
    const days = (new Date(expiryDate).getTime() - Date.now()) / 86400000;
    return days < 0 ? 'text-danger fw-semibold' : days <= 30 ? 'text-warning fw-semibold' : '';
  }
}

import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { ClientService } from '../client.service';
import { Client } from '../client.model';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { PermissionService } from '../../../core/services/permission.service';
import { ExportService } from '../../../core/services/export.service';

@Component({
  selector: 'app-client-list',
  templateUrl: './client-list.html',
  styleUrls: ['./client-list.scss'],
  standalone: false
})
export class ClientListComponent implements OnInit {
  clients: Client[] = [];
  isLoading = false;
  searchQuery = '';
  canAccessWizard = false;

  constructor(
    private clientService: ClientService,
    private swal: SweetAlertService,
    private permissionService: PermissionService,
    private cdr: ChangeDetectorRef,
    private exportService: ExportService
  ) { }

  ngOnInit(): void {
    this.canAccessWizard = this.permissionService.hasAnyPermission(['manage_company', 'manage_users']);
    this.loadClients();
  }

  loadClients() {
    this.isLoading = true;
    const params: any = {};
    if (this.searchQuery) {
      params.q = this.searchQuery;
    }

    this.clientService.getClients(params).subscribe({
      next: (data) => {
        this.clients = data;
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error(err);
        this.isLoading = false;
        this.swal.error('Error al cargar clientes');
        this.cdr.detectChanges();
      }
    });
  }

  deleteClient(id: string) {
    this.swal.confirm('¿Estás seguro?', 'No podrás revertir esto').then((result) => {
      if (result.isConfirmed) {
        this.clientService.deleteClient(id).subscribe({
          next: () => {
            this.swal.success('Cliente eliminado');
            this.loadClients();
          },
          error: () => this.swal.error('Error al eliminar')
        });
      }
    });
  }

  exportData(format: 'excel' | 'csv') {
    this.exportService.download('/clients/export', format);
  }
}

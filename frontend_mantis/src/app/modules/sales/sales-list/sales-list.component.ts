import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgbDropdownModule } from '@ng-bootstrap/ng-bootstrap';
import Swal from 'sweetalert2';
import { SaleService, Sale } from '../../../core/services/sale.service';
import { PermissionService } from '../../../core/services/permission.service';
import { ExportService } from '../../../core/services/export.service';
import { IntegrationService, IntegrationSource } from '../../../core/services/integration.service';
import { StorefrontAdminService, Storefront } from '../../../core/services/storefront-admin.service';
import { SkeletonComponent } from '../../../theme/shared/components/skeleton/skeleton.component';

@Component({
    selector: 'app-sales-list',
    standalone: true,
    imports: [CommonModule, RouterModule, FormsModule, NgbDropdownModule, SkeletonComponent],
    templateUrl: './sales-list.component.html',
    styles: [`
        .status-badge { font-size: 0.8rem; padding: 5px 10px; border-radius: 4px; }
        .bg-quote { background-color: #6c757d; color: white; }
        .bg-confirmed { background-color: #ffc107; color: black; }
        .bg-dispatched { background-color: #17a2b8; color: white; }
        .bg-delivered { background-color: #28a745; color: white; }
        .bg-cancelled { background-color: #dc3545; color: white; }
    `]
})
export class SalesListComponent implements OnInit {
    sales: Sale[] = [];
    loading = false;
    filterStatus = '';
    filterStorefrontId = '';
    filterPaymentStatus = '';
    filterPaymentProvider = '';
    onlineOnly = false;
    storefronts: Storefront[] = [];
    canCreateSales = false;
    canManageCompany = false;
    elegantHomeSources: IntegrationSource[] = [];

    // Inject services
    private saleService = inject(SaleService);
    private permissionService = inject(PermissionService);
    private cdr = inject(ChangeDetectorRef);
    private exportService = inject(ExportService);
    private integrationService = inject(IntegrationService);
    private storefrontAdminService = inject(StorefrontAdminService);

    ngOnInit() {
        this.canCreateSales = this.permissionService.hasPermission('create_sales');
        this.canManageCompany = this.permissionService.hasPermission('manage_company');
        this.loadSales();
        if (this.canManageCompany) {
            this.loadElegantHomeSources();
            this.loadStorefronts();
        }
    }

    loadStorefronts() {
        this.storefrontAdminService.getStorefronts().subscribe({
            next: (storefronts) => {
                this.storefronts = storefronts;
                this.cdr.detectChanges();
            },
            error: () => {
                this.storefronts = [];
            }
        });
    }

    loadElegantHomeSources() {
        this.integrationService.listSources().subscribe({
            next: (sources) => {
                this.elegantHomeSources = sources.filter((source) => source.provider_key === 'eleganthome' && source.is_active);
            },
            error: () => {
                this.elegantHomeSources = [];
            }
        });
    }

    async exportToElegantHome(sale: Sale) {
        if (sale.origin_channel === 'EXTERNAL_APP') return;
        if (!this.elegantHomeSources.length) {
            await Swal.fire('Sin conexión', 'Instala ElegantHome y crea una conexión activa antes de exportar órdenes.', 'info');
            return;
        }
        let sourceId = this.elegantHomeSources[0].id;
        if (this.elegantHomeSources.length > 1) {
            const inputOptions: Record<string, string> = {};
            for (const source of this.elegantHomeSources) inputOptions[source.id] = source.name;
            const selection = await Swal.fire({
                title: 'Elige la conexión ElegantHome',
                input: 'select',
                inputOptions,
                inputValue: sourceId,
                showCancelButton: true,
                confirmButtonText: 'Exportar',
                cancelButtonText: 'Cancelar'
            });
            if (!selection.isConfirmed || !selection.value) return;
            sourceId = selection.value;
        }
        const confirmation = await Swal.fire({
            title: 'Crear orden en ElegantHome',
            text: 'La API externa validará cliente, dirección, precios y stock antes de crearla.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Crear orden',
            cancelButtonText: 'Cancelar'
        });
        if (!confirmation.isConfirmed) return;
        this.loading = true;
        this.integrationService.exportSale(sourceId, sale.id).subscribe({
            next: (link) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Orden creada', `ElegantHome: ${link.external_number || link.external_order_id}`, 'success');
            },
            error: (err) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('No se pudo crear', err?.error?.detail || 'ElegantHome rechazó la orden.', 'error');
            }
        });
    }

    loadSales() {
        this.loading = true;
        this.saleService.getSales(this.filterStatus, undefined, {
            storefrontId: this.filterStorefrontId || undefined,
            onlineOnly: this.onlineOnly,
            paymentStatus: this.filterPaymentStatus || undefined,
            paymentProvider: this.filterPaymentProvider || undefined
        }).subscribe({
            next: (data) => {
                this.sales = data;
                this.loading = false;
                this.cdr.detectChanges(); // Force UI update
            },
            error: (e) => {
                console.error(e);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    getStatusClass(status: string): string {
        switch (status) {
            case 'QUOTE': return 'badge bg-secondary';
            case 'DRAFT': return 'badge bg-light text-dark';
            case 'CONFIRMED': return 'badge bg-warning text-dark';
            case 'PICKING': return 'badge bg-info text-dark';
            case 'PACKING': return 'badge bg-info text-white';
            case 'DISPATCHED': return 'badge bg-primary text-white';
            case 'DELIVERED': return 'badge bg-success';
            case 'COMPLETED': return 'badge bg-success';
            case 'CANCELLED': return 'badge bg-danger';
            default: return 'badge bg-secondary';
        }
    }

    getStatusLabel(status: string): string {
        switch (status) {
            case 'QUOTE': return 'Cotización';
            case 'DRAFT': return 'Borrador';
            case 'CONFIRMED': return 'Confirmada';
            case 'PICKING': return 'En Picking';
            case 'PACKING': return 'Empacando';
            case 'DISPATCHED': return 'Despachada';
            case 'DELIVERED': return 'Entregada';
            case 'COMPLETED': return 'Completada';
            case 'CANCELLED': return 'Cancelada';
            default: return status;
        }
    }

    getPaymentStatusClass(status?: string): string {
        switch ((status || '').toLowerCase()) {
            case 'approved':
            case 'approved_partial': return 'badge bg-success';
            case 'pending':
            case 'shipping_quote_required': return 'badge bg-warning text-dark';
            case 'declined':
            case 'rejected':
            case 'cancelled':
            case 'expired':
            case 'approved_stock_unavailable': return 'badge bg-danger';
            default: return 'badge bg-secondary';
        }
    }

    getPaymentStatusLabel(status?: string): string {
        switch ((status || '').toLowerCase()) {
            case 'approved': return 'Aprobado';
            case 'approved_partial': return 'Aprobado parcial';
            case 'pending': return 'Pendiente';
            case 'shipping_quote_required': return 'Pendiente de envío';
            case 'declined': return 'Rechazado';
            case 'rejected': return 'Rechazado';
            case 'cancelled': return 'Cancelado';
            case 'expired': return 'Vencido';
            case 'approved_stock_unavailable': return 'Aprobado sin stock';
            default: return status || 'No aplica';
        }
    }

    getPaymentProviderLabel(provider?: string): string {
        switch ((provider || '').toLowerCase()) {
            case 'wompi': return 'Wompi';
            case 'payu': return 'PayU';
            case 'mercadopago': return 'Mercado Pago';
            case 'addi': return 'Addi';
            case 'sistecredito': return 'Sistecrédito';
            case 'manual_transfer': return 'Transferencia manual';
            case 'cod': return 'Contraentrega';
            case 'whatsapp': return 'WhatsApp';
            default: return provider || '—';
        }
    }

    getSaleCustomerName(sale: Sale): string {
        return sale.storefront_customer_name || sale.client?.name || 'Cliente ocasional';
    }

    isOnlineSale(sale: Sale): boolean {
        return Boolean(sale.storefront_id || sale.storefront_customer_email || sale.origin_channel === 'STOREFRONT');
    }

    deleteSale(id: string) {
        Swal.fire({
            title: '¿Estás seguro?',
            text: 'Esta acción no se puede deshacer. Solo se pueden eliminar borradores o canceladas.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.loading = true;
                this.saleService.deleteSale(id).subscribe({
                    next: () => {
                        this.sales = this.sales.filter(s => s.id !== id);
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Eliminado', 'La venta ha sido eliminada.', 'success');
                    },
                    error: (err) => {
                        this.loading = false;
                        this.cdr.detectChanges();
                        Swal.fire('Error', 'No se pudo eliminar: ' + (err.error?.detail || err.message), 'error');
                    }
                });
            }
        });
    }

    downloadPdf(id: string, type: string) {
        this.loading = true;
        this.saleService.downloadPdf(id, type).subscribe({
            next: (blob) => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${type}_${id.substring(0, 8)}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('Download error:', err);
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'Error al descargar el PDF. Verifique el estado de la venta.', 'error');
            }
        });
    }

    exportData(format: 'excel' | 'csv') {
        const params: Record<string, string> = {};
        if (this.filterStatus) params['status'] = this.filterStatus;
        if (this.filterStorefrontId) params['storefront_id'] = this.filterStorefrontId;
        if (this.onlineOnly) params['online_only'] = 'true';
        if (this.filterPaymentStatus) params['payment_status'] = this.filterPaymentStatus;
        if (this.filterPaymentProvider) params['payment_provider'] = this.filterPaymentProvider;
        this.exportService.download('/sales/export', format, params);
    }
}

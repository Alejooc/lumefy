import { ChangeDetectorRef, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

import { AuthService, User } from '../../core/services/auth.service';
import { BranchService, Branch } from '../../core/services/branch.service';
import { ClientService } from '../clients/client.service';
import { Client } from '../clients/client.model';
import { POSCartItem, POSCheckout, POSConfig, POSDailyCloseSummary, POSProduct, POSSession, POSSessionListItem, POSSessionStats, PosService } from '../../core/services/pos.service';
import { ReceiptTicketComponent } from './components/receipt-ticket/receipt-ticket.component';
import { PermissionService } from '../../core/services/permission.service';

interface PosReceipt {
    id: string;
    total: number;
    change: number;
    items: POSCartItem[];
    payment_method: string;
    amount_paid: number | null;
    date: Date;
}

interface SessionUserOption {
    id: string;
    name: string;
}

interface SessionsOperationalSummary {
    openNow: number;
    closedToday: number;
    overShortToday: number;
    threshold: number;
    alertCount: number;
}

@Component({
    selector: 'app-pos',
    standalone: true,
    imports: [CommonModule, FormsModule, ReceiptTicketComponent, RouterModule],
    templateUrl: './pos.component.html',
    styleUrls: ['./pos.component.scss']
})
export class PosComponent implements OnInit {
    products: POSProduct[] = [];
    filteredProducts: POSProduct[] = [];
    searchQuery = '';

    cart: POSCartItem[] = [];
    selectedClientId = '';
    clients: Client[] = [];

    currentUser: User | null = null;
    currentBranchId = '';
    branches: Branch[] = [];

    categories: string[] = [];
    selectedCategory = '';

    currentSession: POSSession | null = null;
    posConfig: POSConfig = {
        show_sessions_manager: true,
        session_visibility_scope: 'branch',
        allow_multiple_open_sessions_per_branch: true,
        allow_enter_other_user_session: false,
        require_manager_for_void: true,
        allow_reopen_closed_sessions: true,
        over_short_alert_threshold: 20
    };
    sessions: POSSessionListItem[] = [];
    showSessionsModal = false;
    sessionsFilter: '' | 'OPEN' | 'CLOSED' = '';
    sessionsUserFilter = '';
    sessionsOpenedFrom = '';
    sessionsOpenedTo = '';
    sessionUserOptions: SessionUserOption[] = [];
    loadingSessions = false;

    showCheckoutModal = false;
    showDailyCloseModal = false;
    paymentMethod = 'CASH';
    amountPaid: number | null = null;
    changeAmount = 0;

    showReceipt = false;
    lastSale: PosReceipt | null = null;
    dailyClose: POSDailyCloseSummary | null = null;
    dailyCloseLoading = false;
    canViewDailyClose = false;
    canVoidSales = false;
    canManageSales = false;
    sessionsOpsSummary: SessionsOperationalSummary = {
        openNow: 0,
        closedToday: 0,
        overShortToday: 0,
        threshold: 20,
        alertCount: 0
    };

    mobileTab: 'products' | 'cart' = 'products';
    private readonly branchStorageKey = 'pos_branch_id';

    private posService = inject(PosService);
    private authService = inject(AuthService);
    private permissionService = inject(PermissionService);
    private clientService = inject(ClientService);
    private branchService = inject(BranchService);
    private cdr = inject(ChangeDetectorRef);

    @ViewChild('searchInput') searchInput!: ElementRef;

    ngOnInit() {
        this.currentUser = this.authService.currentUserValue;
        this.canViewDailyClose = this.permissionService.hasAnyPermission(['view_reports', 'manage_sales']);
        this.canVoidSales = this.permissionService.hasPermission('manage_sales');
        this.canManageSales = this.permissionService.hasPermission('manage_sales');
        const storedBranch = localStorage.getItem(this.branchStorageKey) || '';
        this.currentBranchId = this.currentUser?.branch_id || storedBranch;

        this.loadPosConfig();
        this.loadBranches();
        this.loadClients();
    }

    loadPosConfig() {
        this.posService.getConfig().subscribe({
            next: (cfg) => {
                this.posConfig = cfg;
                this.sessionsOpsSummary.threshold = Number(cfg.over_short_alert_threshold || 20);
                this.cdr.detectChanges();
            },
            error: () => {
                this.cdr.detectChanges();
            }
        });
    }

    loadBranches() {
        this.branchService.getBranches().subscribe((data) => {
            this.branches = data;
            if (!this.currentBranchId && this.branches.length > 0) {
                this.currentBranchId = this.branches[0].id;
            }
            if (this.currentBranchId && !this.branches.some((b) => b.id === this.currentBranchId)) {
                this.currentBranchId = this.branches[0]?.id || '';
            }
            if (this.currentBranchId) {
                localStorage.setItem(this.branchStorageKey, this.currentBranchId);
                this.loadProducts();
                this.loadCurrentSession();
                this.loadSessions();
                this.loadSessionsOperationalSummary();
            }
            this.cdr.detectChanges();
        });
    }

    loadClients() {
        this.clientService.getClients().subscribe((data) => {
            this.clients = data;
            this.cdr.detectChanges();
        });
    }

    onBranchChange() {
        this.cart = [];
        this.currentSession = null;
        this.sessions = [];
        if (this.currentBranchId) {
            localStorage.setItem(this.branchStorageKey, this.currentBranchId);
        } else {
            localStorage.removeItem(this.branchStorageKey);
        }
        if (this.currentBranchId) {
            this.loadProducts();
            this.loadCurrentSession();
            this.loadSessions();
            this.loadSessionsOperationalSummary();
        } else {
            this.products = [];
            this.filteredProducts = [];
        }
    }

    loadCurrentSession() {
        if (!this.currentBranchId) return;
        this.posService.getCurrentSession(this.currentBranchId).subscribe({
            next: (session) => {
                this.currentSession = session;
                this.cdr.detectChanges();
            },
            error: () => {
                this.currentSession = null;
                this.cdr.detectChanges();
            }
        });
    }

    loadProducts() {
        this.posService.getProducts(this.currentBranchId).subscribe((data) => {
            this.products = data;
            const cats = data.map((p) => p.category_name).filter((c): c is string => !!c);
            this.categories = [...new Set(cats)].sort();
            this.selectedCategory = '';
            this.filteredProducts = data;
            this.cdr.detectChanges();
        });
    }

    selectCategory(cat: string) {
        this.selectedCategory = cat;
        this.filterProducts();
    }

    filterProducts() {
        const query = this.searchQuery.toLowerCase();
        this.filteredProducts = this.products.filter((p) => {
            const matchesSearch = !query || p.name.toLowerCase().includes(query) || (p.barcode && p.barcode.includes(query)) || (p.sku && p.sku.toLowerCase().includes(query));
            const matchesCategory = !this.selectedCategory || p.category_name === this.selectedCategory;
            return matchesSearch && matchesCategory;
        });

        if (this.searchQuery && this.filteredProducts.length === 1 && this.filteredProducts[0].barcode === this.searchQuery) {
            this.addToCart(this.filteredProducts[0]);
            this.searchQuery = '';
            this.filterProducts();
        }
    }

    addToCart(product: POSProduct) {
        if (!this.currentSession) {
            Swal.fire('Caja cerrada', 'Debes abrir caja antes de vender en POS.', 'warning');
            return;
        }
        if (product.stock <= 0) {
            Swal.fire('Sin Stock', `El producto ${product.name} no tiene existencias.`, 'warning');
            return;
        }

        const existingItem = this.cart.find((item) => item.product_id === product.id);
        if (existingItem) {
            if (existingItem.quantity >= product.stock) {
                Swal.fire('Limite', 'No puedes agregar mas unidades de las disponibles en stock.', 'warning');
                return;
            }
            existingItem.quantity += 1;
        } else {
            this.cart.push({
                product_id: product.id,
                quantity: 1,
                price: product.price,
                discount: 0,
                _tempProduct: product
            });
        }
        this.cdr.detectChanges();
    }

    updateQuantity(item: POSCartItem, delta: number) {
        const product = this.products.find((p) => p.id === item.product_id);
        if (!product) return;

        const newQty = item.quantity + delta;
        if (newQty <= 0) {
            this.removeItem(item);
        } else if (newQty > product.stock) {
            Swal.fire('Limite', 'Stock insuficiente', 'warning');
        } else {
            item.quantity = newQty;
        }
    }

    removeItem(item: POSCartItem) {
        this.cart = this.cart.filter((i) => i !== item);
    }

    clearCart() {
        this.cart = [];
    }

    get subtotal() {
        return this.cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
    }

    get totalDiscount() {
        return this.cart.reduce((sum, item) => sum + item.discount, 0);
    }

    get total() {
        return this.subtotal - this.totalDiscount;
    }

    openCheckout() {
        if (this.cart.length === 0) return;
        if (!this.currentSession) {
            Swal.fire('Caja cerrada', 'Debes abrir caja antes de cobrar.', 'warning');
            return;
        }
        if (!this.currentBranchId) {
            Swal.fire('Error', 'Debe seleccionar una sucursal.', 'error');
            return;
        }
        this.amountPaid = this.total;
        this.paymentMethod = 'CASH';
        this.calculateChange();
        this.showCheckoutModal = true;
    }

    closeCheckout() {
        this.showCheckoutModal = false;
    }

    openDailyClose() {
        if (!this.canViewDailyClose) {
            Swal.fire('Sin permiso', 'No tienes permisos para ver el cierre del dia.', 'warning');
            return;
        }
        const targetDate = new Date().toISOString().slice(0, 10);
        this.showDailyCloseModal = true;
        this.dailyCloseLoading = true;
        this.dailyClose = null;
        this.posService.getDailyClose(targetDate, this.currentBranchId || undefined).subscribe({
            next: (data) => {
                this.dailyClose = data;
                this.dailyCloseLoading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                this.dailyCloseLoading = false;
                this.showDailyCloseModal = false;
                Swal.fire('Error', err.error?.detail || 'No se pudo cargar el cierre del dia.', 'error');
            }
        });
    }

    closeDailyClose() {
        this.showDailyCloseModal = false;
    }

    exportDailyCloseCsv() {
        if (!this.dailyClose) return;
        const columns = [
            'Fecha',
            'Sucursal',
            'Ventas',
            'Bruto',
            'Efectivo',
            'Tarjeta',
            'Credito',
            'Devoluciones',
            'Total_Devoluciones',
            'Neto',
            'Cajas_Abiertas_Hoy',
            'Cajas_Cerradas_Hoy',
            'Apertura_Total',
            'Esperado_Total',
            'Contado_Total',
            'Diferencia_Total',
            'Cajas_Abiertas_Ahora'
        ];
        const row = [
            this.dailyClose.date,
            this.currentBranchId || 'todas',
            this.dailyClose.sales_count,
            this.dailyClose.gross_sales,
            this.dailyClose.payments_cash,
            this.dailyClose.payments_card,
            this.dailyClose.payments_credit,
            this.dailyClose.returns_count,
            this.dailyClose.total_refunds,
            this.dailyClose.net_sales,
            this.dailyClose.sessions_opened_count,
            this.dailyClose.sessions_closed_count,
            this.dailyClose.opening_amount_total,
            this.dailyClose.expected_amount_total,
            this.dailyClose.counted_amount_total,
            this.dailyClose.over_short_total,
            this.dailyClose.open_sessions_now
        ];

        let csvContent = 'data:text/csv;charset=utf-8,';
        csvContent += `${columns.join(',')}\n${row.join(',')}\n`;
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement('a');
        link.setAttribute('href', encodedUri);
        link.setAttribute('download', `pos_cierre_diario_${this.dailyClose.date}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    calculateChange() {
        if (this.amountPaid !== null) {
            this.changeAmount = this.amountPaid - this.total;
        }
    }

    setExactAmount() {
        this.amountPaid = this.total;
        this.calculateChange();
    }

    quickAmount(amount: number) {
        this.amountPaid = amount;
        this.calculateChange();
    }

    processPayment() {
        if (!this.currentSession) {
            Swal.fire('Caja cerrada', 'Debes abrir caja antes de cobrar.', 'warning');
            return;
        }
        if (this.amountPaid === null || this.amountPaid < this.total) {
            if (this.paymentMethod !== 'CREDIT') {
                Swal.fire('Error', 'El monto pagado es menor al total de la venta.', 'error');
                return;
            }
        }

        const payload: POSCheckout = {
            branch_id: this.currentBranchId,
            client_id: this.selectedClientId || undefined,
            items: this.cart.map((i) => ({
                product_id: i.product_id,
                quantity: i.quantity,
                price: i.price,
                discount: i.discount
            })),
            payment_method: this.paymentMethod,
            amount_paid: this.paymentMethod === 'CREDIT' ? 0 : this.amountPaid!
        };

        this.posService.checkout(payload).subscribe({
            next: (res) => {
                this.closeCheckout();

                this.lastSale = {
                    id: res.sale_id,
                    total: res.total,
                    change: res.change,
                    items: this.cart.map((i) => ({ ...i })),
                    payment_method: this.paymentMethod,
                    amount_paid: this.amountPaid,
                    date: new Date()
                };

                this.clearCart();
                this.loadProducts();
                this.loadCurrentSession();
                this.loadSessions();
                this.showReceipt = true;

                Swal.fire({
                    title: 'Venta Completada',
                    text: `Cambio: $${res.change.toFixed(2)}`,
                    icon: 'success',
                    timer: 2500,
                    showConfirmButton: false
                });
            },
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'Error al procesar el pago', 'error');
            }
        });
    }

    openCashSession() {
        if (!this.currentBranchId) {
            Swal.fire('Sucursal requerida', 'Selecciona una sucursal antes de abrir caja.', 'warning');
            return;
        }
        Swal.fire({
            title: 'Abrir caja',
            html: `
              <label class="form-label">Monto inicial</label>
              <input id="opening_amount" type="number" step="0.01" min="0" class="swal2-input" value="0" />
              <label class="form-label mt-2">Nota (opcional)</label>
              <input id="opening_note" type="text" class="swal2-input" placeholder="Ej: Fondo inicial turno manana" />
            `,
            showCancelButton: true,
            confirmButtonText: 'Abrir caja',
            preConfirm: () => {
                const amountRaw = (document.getElementById('opening_amount') as HTMLInputElement)?.value;
                const note = (document.getElementById('opening_note') as HTMLInputElement)?.value;
                const openingAmount = Number(amountRaw || 0);
                if (openingAmount < 0) {
                    Swal.showValidationMessage('El monto inicial no puede ser negativo.');
                    return null;
                }
                return { openingAmount, note };
            }
        }).then((result) => {
            if (!result.isConfirmed || !result.value) return;
            this.posService.openSession(this.currentBranchId, result.value.openingAmount, result.value.note).subscribe({
                next: (session) => {
                    this.currentSession = session;
                    this.loadSessions();
                    this.cdr.detectChanges();
                    Swal.fire('Caja activa', 'Caja lista para vender en POS.', 'success');
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo abrir la caja.', 'error');
                }
            });
        });
    }

    closeCashSession() {
        if (!this.currentSession) {
            Swal.fire('Sin caja abierta', 'No hay una sesion de caja activa.', 'info');
            return;
        }
        this.openCloseSessionDialog(this.currentSession.id, () => {
            this.currentSession = null;
            this.cart = [];
            this.loadCurrentSession();
            this.loadSessions();
            this.cdr.detectChanges();
        });
    }

    printReceipt() {
        window.print();
    }

    closeReceipt() {
        this.showReceipt = false;
        this.lastSale = null;
    }

    voidLastSale() {
        if (!this.lastSale) return;
        if (this.posConfig.require_manager_for_void && !this.canVoidSales) {
            Swal.fire('Sin permiso', 'Esta anulación requiere permiso de gestion de ventas.', 'warning');
            return;
        }
        Swal.fire({
            title: 'Anular venta',
            html: `
              <label class="form-label">Motivo</label>
              <input id="void_reason" type="text" class="swal2-input" placeholder="Ej: Error de cobro" />
            `,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'Anular',
            preConfirm: () => {
                const reason = (document.getElementById('void_reason') as HTMLInputElement)?.value;
                return reason || 'Anulacion solicitada desde POS';
            }
        }).then((result) => {
            if (!result.isConfirmed || !this.lastSale) return;
            this.posService.voidSale(this.lastSale.id, result.value).subscribe({
                next: (res) => {
                    Swal.fire('Venta anulada', res.detail, 'success');
                    this.loadProducts();
                    this.loadCurrentSession();
                    this.loadSessions();
                    this.closeReceipt();
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo anular la venta.', 'error');
                }
            });
        });
    }

    loadSessions() {
        this.loadingSessions = true;
        this.posService.listSessions({
            branchId: this.currentBranchId || undefined,
            status: this.sessionsFilter || undefined,
            userId: this.sessionsUserFilter || undefined,
            openedFrom: this.sessionsOpenedFrom || undefined,
            openedTo: this.sessionsOpenedTo || undefined,
            limit: 200
        }).subscribe({
            next: (rows) => {
                this.sessions = rows;
                this.recomputeSessionAlerts();
                this.loadingSessions = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.sessions = [];
                this.recomputeSessionAlerts();
                this.loadingSessions = false;
                this.cdr.detectChanges();
            }
        });
    }

    openSessionsManager() {
        if (!this.posConfig.show_sessions_manager) {
            Swal.fire('No disponible', 'El gestor de cajas esta deshabilitado en configuracion POS.', 'info');
            return;
        }
        this.showSessionsModal = true;
        this.refreshSessionUserOptions();
        this.loadSessions();
        this.loadSessionsOperationalSummary();
    }

    closeSessionsManager() {
        this.showSessionsModal = false;
    }

    onSessionFilterChange(filter: '' | 'OPEN' | 'CLOSED') {
        this.sessionsFilter = filter;
        this.loadSessions();
    }

    applySessionsAdvancedFilters() {
        if (this.sessionsOpenedFrom && this.sessionsOpenedTo && this.sessionsOpenedFrom > this.sessionsOpenedTo) {
            Swal.fire('Rango invalido', 'La fecha inicial no puede ser mayor a la fecha final.', 'warning');
            return;
        }
        this.loadSessions();
    }

    resetSessionsAdvancedFilters() {
        this.sessionsUserFilter = '';
        this.sessionsOpenedFrom = '';
        this.sessionsOpenedTo = '';
        this.sessionsFilter = '';
        this.loadSessions();
    }

    reopenSession(session: POSSessionListItem) {
        if (!this.canManageSales || !this.posConfig.allow_reopen_closed_sessions) {
            Swal.fire('No permitido', 'No tienes permisos para reabrir cajas.', 'warning');
            return;
        }
        if (session.status !== 'CLOSED') {
            Swal.fire('No disponible', 'Solo se pueden reabrir cajas cerradas.', 'info');
            return;
        }
        Swal.fire({
            title: 'Reabrir caja',
            html: `
              <p class="text-start mb-2"><strong>Sesion:</strong> ${session.id}</p>
              <p class="text-start mb-2"><strong>Diferencia registrada:</strong> ${Number(session.over_short || 0).toFixed(2)}</p>
              <label class="form-label">Motivo obligatorio</label>
              <input id="reopen_reason" type="text" class="swal2-input" placeholder="Ej: Correccion de arqueo" />
            `,
            showCancelButton: true,
            confirmButtonText: 'Reabrir',
            preConfirm: () => {
                const reason = ((document.getElementById('reopen_reason') as HTMLInputElement)?.value || '').trim();
                if (!reason) {
                    Swal.showValidationMessage('Debes escribir un motivo para la reapertura.');
                    return null;
                }
                return { reason };
            }
        }).then((result) => {
            if (!result.isConfirmed || !result.value) return;
            this.posService.reopenSession(session.id, result.value.reason).subscribe({
                next: () => {
                    this.loadCurrentSession();
                    this.loadSessions();
                    this.loadSessionsOperationalSummary();
                    Swal.fire('Caja reabierta', 'La caja fue reabierta con auditoria registrada.', 'success');
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo reabrir la caja.', 'error');
                }
            });
        });
    }

    exportSessionsCsv() {
        this.exportSessionRowsCsv(this.sessions, 'pos_historial_cajas');
    }

    exportClosedSessionsCsv() {
        this.exportSessionRowsCsv(this.closedSessions, 'pos_cajas_cerradas');
    }

    exportMyOpenSessionsCsv() {
        this.exportSessionRowsCsv(this.myOpenSessions, 'pos_mis_cajas_abiertas');
    }

    private exportSessionRowsCsv(rows: POSSessionListItem[], filenamePrefix: string) {
        if (!rows.length) {
            Swal.fire('Sin datos', 'No hay cajas para exportar con los filtros actuales.', 'info');
            return;
        }

        const columns = [
            'id',
            'sucursal',
            'cajero',
            'estado',
            'apertura',
            'cierre',
            'monto_inicial',
            'ventas_total',
            'ventas_efectivo',
            'transacciones',
            'esperado',
            'contado',
            'diferencia'
        ];

        const lines = rows.map((s) => [
            s.id,
            s.branch_name || '',
            s.user_name || '',
            s.status,
            s.opened_at ? new Date(s.opened_at).toISOString() : '',
            s.closed_at ? new Date(s.closed_at).toISOString() : '',
            Number(s.opening_amount || 0).toFixed(2),
            Number(s.total_sales || 0).toFixed(2),
            Number(s.cash_sales_total || 0).toFixed(2),
            String(s.transactions_count || 0),
            Number(s.expected_amount || 0).toFixed(2),
            Number(s.counted_amount || 0).toFixed(2),
            Number(s.over_short || 0).toFixed(2)
        ]);

        const csvRows = [columns, ...lines].map((row) => row.map((cell) => this.csvEscape(cell)).join(','));
        const csv = `data:text/csv;charset=utf-8,${csvRows.join('\n')}\n`;
        const href = encodeURI(csv);
        const datePart = new Date().toISOString().slice(0, 10);
        const link = document.createElement('a');
        link.setAttribute('href', href);
        link.setAttribute('download', `${filenamePrefix}_${datePart}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    get myOpenSessions(): POSSessionListItem[] {
        if (!this.currentUser) return [];
        return this.sessions.filter((s) => s.status === 'OPEN' && s.user_id === this.currentUser?.id);
    }

    get branchOpenSessions(): POSSessionListItem[] {
        if (!this.currentBranchId) return [];
        return this.sessions.filter((s) => s.status === 'OPEN' && s.branch_id === this.currentBranchId);
    }

    isOwnSession(session: POSSessionListItem): boolean {
        return !!this.currentUser && session.user_id === this.currentUser.id;
    }

    enterSession(session: POSSessionListItem) {
        if (!this.currentUser) return;
        if (session.status !== 'OPEN') {
            Swal.fire('Caja cerrada', 'Solo puedes entrar en cajas abiertas.', 'info');
            return;
        }
        if (session.user_id !== this.currentUser.id && !this.posConfig.allow_enter_other_user_session) {
            Swal.fire('No permitido', 'Solo puedes entrar en tu propia caja.', 'warning');
            return;
        }
        this.currentBranchId = session.branch_id;
        localStorage.setItem(this.branchStorageKey, this.currentBranchId);
        this.loadProducts();
        this.loadCurrentSession();
        this.showSessionsModal = false;
    }

    closeListedSession(session: POSSessionListItem) {
        if (!this.isOwnSession(session)) {
            Swal.fire('No permitido', 'Solo puedes cerrar tus propias cajas.', 'warning');
            return;
        }
        if (session.status !== 'OPEN') {
            Swal.fire('No disponible', 'La caja ya esta cerrada.', 'info');
            return;
        }

        this.openCloseSessionDialog(session.id, () => {
            if (this.currentSession?.id === session.id) {
                this.currentSession = null;
                this.cart = [];
            }
            this.loadCurrentSession();
            this.loadSessions();
        });
    }

    viewSessionStats(session: POSSessionListItem) {
        this.posService.getSessionStats(session.id).subscribe({
            next: (stats) => {
                const auditBlock = stats.closing_audit ? `
                        <hr/>
                        <div><strong>Foto cierre:</strong></div>
                        <div><strong>Tx cierre:</strong> ${Number(stats.closing_audit.transactions_count || 0)}</div>
                        <div><strong>Efectivo cierre:</strong> ${Number(stats.closing_audit.cash_sales_total || 0).toFixed(2)}</div>
                        <div><strong>Tarjeta cierre:</strong> ${Number(stats.closing_audit.card_sales_total || 0).toFixed(2)}</div>
                        <div><strong>Credito cierre:</strong> ${Number(stats.closing_audit.credit_sales_total || 0).toFixed(2)}</div>
                ` : '';
                const reopenBlock = stats.reopen_audit ? `
                        <hr/>
                        <div><strong>Reapertura:</strong></div>
                        <div><strong>Fecha:</strong> ${stats.reopen_audit.reopened_at ? new Date(stats.reopen_audit.reopened_at).toLocaleString() : '-'}</div>
                        <div><strong>Motivo:</strong> ${stats.reopen_audit.reason || '-'}</div>
                ` : '';
                Swal.fire({
                    title: `Caja ${stats.status === 'OPEN' ? 'abierta' : 'cerrada'}`,
                    html: `
                      <div style="text-align:left;line-height:1.5">
                        <div><strong>Sucursal:</strong> ${stats.branch_name || '-'}</div>
                        <div><strong>Cajero:</strong> ${stats.user_name || '-'}</div>
                        <div><strong>Apertura:</strong> ${new Date(stats.opened_at).toLocaleString()}</div>
                        <div><strong>Cierre:</strong> ${stats.closed_at ? new Date(stats.closed_at).toLocaleString() : '-'}</div>
                        <hr/>
                        <div><strong>Ventas:</strong> ${stats.total_sales.toFixed(2)}</div>
                        <div><strong>Transacciones:</strong> ${stats.transactions_count}</div>
                        <div><strong>Ticket promedio:</strong> ${stats.average_ticket.toFixed(2)}</div>
                        <div><strong>Efectivo:</strong> ${stats.cash_sales_total.toFixed(2)}</div>
                        <div><strong>Tarjeta:</strong> ${stats.card_sales_total.toFixed(2)}</div>
                        <div><strong>Credito:</strong> ${stats.credit_sales_total.toFixed(2)}</div>
                        <hr/>
                        <div><strong>Monto inicial:</strong> ${stats.opening_amount.toFixed(2)}</div>
                        <div><strong>Esperado en caja:</strong> ${stats.expected_amount.toFixed(2)}</div>
                        <div><strong>Contado:</strong> ${stats.counted_amount.toFixed(2)}</div>
                        <div><strong>Diferencia:</strong> ${stats.over_short.toFixed(2)}</div>
                        ${auditBlock}
                        ${reopenBlock}
                      </div>
                    `,
                    width: 620
                });
            },
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'No se pudieron cargar las estadisticas de caja.', 'error');
            }
        });
    }

    get closedSessions(): POSSessionListItem[] {
        return this.sessions.filter((s) => s.status === 'CLOSED');
    }

    get closedSessionsAuditSummary(): { count: number; totalSales: number; expected: number; counted: number; overShort: number } {
        return this.closedSessions.reduce(
            (acc, s) => {
                acc.count += 1;
                acc.totalSales += Number(s.total_sales || 0);
                acc.expected += Number(s.expected_amount || 0);
                acc.counted += Number(s.counted_amount || 0);
                acc.overShort += Number(s.over_short || 0);
                return acc;
            },
            { count: 0, totalSales: 0, expected: 0, counted: 0, overShort: 0 }
        );
    }

    isOverShortAlert(session: POSSessionListItem): boolean {
        const threshold = Number(this.posConfig.over_short_alert_threshold || 20);
        return Math.abs(Number(session.over_short || 0)) >= threshold && session.status === 'CLOSED';
    }

    private refreshSessionUserOptions() {
        this.posService.listSessions({
            branchId: this.currentBranchId || undefined,
            limit: 200
        }).subscribe({
            next: (rows) => {
                const map = new Map<string, string>();
                for (const row of rows) {
                    if (!row.user_id) continue;
                    map.set(row.user_id, row.user_name || row.user_id);
                }
                this.sessionUserOptions = Array.from(map.entries())
                    .map(([id, name]) => ({ id, name }))
                    .sort((a, b) => a.name.localeCompare(b.name));
                this.cdr.detectChanges();
            },
            error: () => {
                this.sessionUserOptions = [];
                this.cdr.detectChanges();
            }
        });
    }

    private loadSessionsOperationalSummary() {
        if (!this.currentBranchId) return;
        const today = new Date().toISOString().slice(0, 10);
        this.posService.getDailyClose(today, this.currentBranchId).subscribe({
            next: (summary) => {
                this.sessionsOpsSummary.openNow = Number(summary.open_sessions_now || 0);
                this.sessionsOpsSummary.closedToday = Number(summary.sessions_closed_count || 0);
                this.sessionsOpsSummary.overShortToday = Number(summary.over_short_total || 0);
                this.cdr.detectChanges();
            },
            error: () => {
                this.sessionsOpsSummary.openNow = 0;
                this.sessionsOpsSummary.closedToday = 0;
                this.sessionsOpsSummary.overShortToday = 0;
                this.cdr.detectChanges();
            }
        });
    }

    private recomputeSessionAlerts() {
        this.sessionsOpsSummary.alertCount = this.sessions.filter((s) => this.isOverShortAlert(s)).length;
    }

    private openCloseSessionDialog(sessionId: string, onClosed: () => void) {
        this.posService.getSessionStats(sessionId).subscribe({
            next: (stats) => this.confirmCloseWithBreakdown(stats, onClosed),
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'No se pudieron cargar los datos de la caja para cierre.', 'error');
            }
        });
    }

    private confirmCloseWithBreakdown(stats: POSSessionStats, onClosed: () => void) {
        const expectedAmount = Number(stats.expected_amount || 0);
        Swal.fire({
            title: 'Cerrar caja',
            html: `
              <div class="text-start mb-2">
                <div><strong>Monto inicial:</strong> ${Number(stats.opening_amount || 0).toFixed(2)}</div>
                <div><strong>Ventas:</strong> ${Number(stats.total_sales || 0).toFixed(2)}</div>
                <div><strong>Efectivo:</strong> ${Number(stats.cash_sales_total || 0).toFixed(2)}</div>
                <div><strong>Tarjeta:</strong> ${Number(stats.card_sales_total || 0).toFixed(2)}</div>
                <div><strong>Credito:</strong> ${Number(stats.credit_sales_total || 0).toFixed(2)}</div>
                <div><strong>Transacciones:</strong> ${Number(stats.transactions_count || 0)}</div>
                <div class="mt-1"><strong>Esperado en caja:</strong> ${expectedAmount.toFixed(2)}</div>
              </div>
              <label class="form-label">Efectivo contado</label>
              <input id="counted_amount_close" type="number" step="0.01" min="0" class="swal2-input" value="${expectedAmount.toFixed(2)}" />
              <label class="form-label mt-2">Nota de cierre (opcional)</label>
              <input id="closing_note_close" type="text" class="swal2-input" placeholder="Ej: Diferencia por redondeos" />
            `,
            showCancelButton: true,
            confirmButtonText: 'Cerrar caja',
            preConfirm: () => {
                const countedRaw = (document.getElementById('counted_amount_close') as HTMLInputElement)?.value;
                const note = (document.getElementById('closing_note_close') as HTMLInputElement)?.value;
                const countedAmount = Number(countedRaw || 0);
                if (countedAmount < 0) {
                    Swal.showValidationMessage('El efectivo contado no puede ser negativo.');
                    return null;
                }
                return { countedAmount, note };
            }
        }).then((result) => {
            if (!result.isConfirmed || !result.value) return;
            this.posService.closeSession(stats.id, result.value.countedAmount, result.value.note).subscribe({
                next: (closed) => {
                    onClosed();
                    const diff = Number(closed.over_short || 0);
                    Swal.fire(
                        'Caja cerrada',
                        `Esperado: ${closed.expected_amount.toFixed(2)} | Contado: ${closed.counted_amount.toFixed(2)} | Diferencia: ${diff.toFixed(2)}`,
                        diff === 0 ? 'success' : 'warning'
                    );
                },
                error: (err) => {
                    Swal.fire('Error', err.error?.detail || 'No se pudo cerrar la caja.', 'error');
                }
            });
        });
    }

    private csvEscape(value: string): string {
        const raw = String(value ?? '');
        return `"${raw.replace(/"/g, '""')}"`;
    }
}

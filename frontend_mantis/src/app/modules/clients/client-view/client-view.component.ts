import { Component, OnInit, ChangeDetectorRef, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../../core/services/auth.service';
import {
    ClientSaleItem,
    ClientService,
    ClientStatement,
    ClientStats,
    ClientTimelineEntry
} from '../client.service';
import { Client } from '../client.model';

@Component({
    selector: 'app-client-view',
    templateUrl: './client-view.component.html',
    styleUrls: ['./client-view.component.scss'],
    standalone: false
})
export class ClientViewComponent implements OnInit {
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private clientService = inject(ClientService);
    private fb = inject(FormBuilder);
    private sweetAlert = inject(SweetAlertService);
    private auth = inject(AuthService);
    private cdr = inject(ChangeDetectorRef);

    clientId = '';
    client: Client | null = null;
    statement: ClientStatement | null = null;
    stats: ClientStats | null = null;
    timeline: ClientTimelineEntry[] = [];
    sales: ClientSaleItem[] = [];

    isLoading = true;
    isLoadingStatement = false;
    isLoadingTimeline = false;
    isLoadingSales = false;
    isSubmittingPayment = false;
    isSubmittingActivity = false;

    activeTab = 'general';
    activityForm: FormGroup;

    currencySymbol = '$';

    paymentForm: FormGroup;
    showPaymentModal = false;

    constructor() {
        this.paymentForm = this.fb.group({
            amount: [null, [Validators.required, Validators.min(0.01)]],
            reference_id: [''],
            description: ['Abono a cuenta', [Validators.required]]
        });

        this.activityForm = this.fb.group({
            type: ['NOTE', Validators.required],
            content: ['', [Validators.required, Validators.minLength(3)]]
        });
    }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
                this.cdr.detectChanges();
            }
        });

        const routeClientId = this.route.snapshot.paramMap.get('id');
        if (routeClientId) {
            this.clientId = routeClientId;
            this.loadAll();
        } else {
            this.router.navigate(['/clients']);
        }
    }

    loadAll() {
        this.loadClient();
        this.loadStatement();
        this.loadStats();
        this.loadTimeline();
        this.loadSales();
    }

    loadClient() {
        this.clientService.getClient(this.clientId).subscribe({
            next: (data) => {
                this.client = data;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.sweetAlert.error('Error', 'No se pudo cargar el cliente.');
                this.router.navigate(['/clients']);
            }
        });
    }

    loadStatement() {
        this.isLoadingStatement = true;
        this.clientService.getStatement(this.clientId).subscribe({
            next: (data) => {
                this.statement = data;
                this.isLoadingStatement = false;
                if (this.client) {
                    this.client.current_balance = data.current_balance;
                }
                this.cdr.detectChanges();
            },
            error: () => {
                this.isLoadingStatement = false;
                this.cdr.detectChanges();
            }
        });
    }

    loadStats() {
        this.clientService.getStats(this.clientId).subscribe(data => {
            this.stats = data;
            this.cdr.detectChanges();
        });
    }

    loadTimeline() {
        this.isLoadingTimeline = true;
        this.clientService.getTimeline(this.clientId).subscribe(data => {
            this.timeline = data;
            this.isLoadingTimeline = false;
            this.cdr.detectChanges();
        });
    }

    loadSales() {
        this.isLoadingSales = true;
        this.clientService.getSales(this.clientId).subscribe(data => {
            this.sales = data.items;
            this.isLoadingSales = false;
            this.cdr.detectChanges();
        });
    }

    setTab(tab: string) {
        this.activeTab = tab;
        this.cdr.detectChanges();
    }

    openPaymentModal() {
        this.paymentForm.reset({
            amount: this.statement?.current_balance > 0 ? this.statement.current_balance : null,
            description: 'Abono a cuenta',
            reference_id: ''
        });
        this.showPaymentModal = true;
    }

    closePaymentModal() {
        this.showPaymentModal = false;
    }

    submitPayment() {
        if (this.paymentForm.invalid) return;

        this.isSubmittingPayment = true;
        const paymentData = this.paymentForm.value as { amount: number; reference_id?: string; description: string };

        this.clientService.registerPayment(this.clientId, paymentData).subscribe({
            next: () => {
                this.sweetAlert.success('Pago Registrado', 'El abono se registró correctamente.');
                this.isSubmittingPayment = false;
                this.showPaymentModal = false;
                this.loadAll();
            },
            error: (err) => {
                this.isSubmittingPayment = false;
                this.cdr.detectChanges();
                this.sweetAlert.error('Error', err.error?.detail || 'No se pudo registrar el pago.');
            }
        });
    }

    submitActivity() {
        if (this.activityForm.invalid) return;
        this.isSubmittingActivity = true;
        this.clientService.createActivity(this.clientId, this.activityForm.value).subscribe({
            next: () => {
                this.isSubmittingActivity = false;
                this.activityForm.reset({ type: 'NOTE', content: '' });
                this.loadTimeline();
                this.sweetAlert.success('Actividad registrada');
            },
            error: () => {
                this.isSubmittingActivity = false;
                this.cdr.detectChanges();
            }
        });
    }
}

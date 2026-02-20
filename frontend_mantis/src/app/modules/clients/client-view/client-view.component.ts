import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../../core/services/auth.service';
import { ChangeDetectorRef } from '@angular/core';

@Component({
    selector: 'app-client-view',
    templateUrl: './client-view.component.html',
    styleUrls: ['./client-view.component.scss'],
    standalone: false
})
export class ClientViewComponent implements OnInit {
    clientId: string;
    client: any;
    statement: any;
    isLoading = true;
    isLoadingStatement = false;
    isSubmittingPayment = false;
    activeTab = 'general';

    currencySymbol = '$';

    paymentForm: FormGroup;
    showPaymentModal = false;

    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private api: ApiService,
        private fb: FormBuilder,
        private sweetAlert: SweetAlertService,
        private auth: AuthService,
        private cdr: ChangeDetectorRef
    ) {
        this.paymentForm = this.fb.group({
            amount: [null, [Validators.required, Validators.min(0.01)]],
            reference_id: [''],
            description: ['Abono a cuenta', [Validators.required]]
        });
    }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe(company => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
                this.cdr.detectChanges();
            }
        });

        this.clientId = this.route.snapshot.paramMap.get('id');
        if (this.clientId) {
            this.loadClient();
            this.loadStatement();
        } else {
            this.router.navigate(['/clients']);
        }
    }

    loadClient() {
        this.api.get<any>(`/clients/${this.clientId}`).subscribe({
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
        this.api.get<any>(`/clients/${this.clientId}/statement`).subscribe({
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

    setTab(tab: string) {
        this.activeTab = tab;
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
        const paymentData = this.paymentForm.value;

        this.api.post(`/clients/${this.clientId}/payments`, paymentData).subscribe({
            next: () => {
                this.sweetAlert.success('Pago Registrado', 'El abono se registró correctamente.');
                this.isSubmittingPayment = false;
                this.showPaymentModal = false;
                this.cdr.detectChanges();

                // Reload data
                this.loadClient();
                this.loadStatement();
            },
            error: (err) => {
                this.isSubmittingPayment = false;
                this.cdr.detectChanges();
                this.sweetAlert.error('Error', err.error?.detail || 'No se pudo registrar el pago.');
            }
        });
    }
}

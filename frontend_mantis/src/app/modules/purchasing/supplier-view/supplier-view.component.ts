import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { AuthService } from '../../../core/services/auth.service';

@Component({
    selector: 'app-supplier-view',
    standalone: true,
    imports: [CommonModule, RouterModule, ReactiveFormsModule],
    templateUrl: './supplier-view.component.html',
    styleUrls: ['./supplier-view.component.scss']
})
export class SupplierViewComponent implements OnInit {
    supplierId: string | null = null;
    supplier: any;
    statement: any;
    isLoading = true;
    isLoadingStatement = false;
    isSubmittingPayment = false;
    activeTab = 'general';

    currencySymbol = '$';

    paymentForm: FormGroup;
    showPaymentModal = false;

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private api = inject(ApiService);
    private fb = inject(FormBuilder);
    private sweetAlert = inject(SweetAlertService);
    private auth = inject(AuthService);
    private cdr = inject(ChangeDetectorRef);

    constructor() {
        this.paymentForm = this.fb.group({
            amount: [null, [Validators.required, Validators.min(0.01)]],
            reference_id: [''],
            description: ['Abono a proveedor', [Validators.required]]
        });
    }

    ngOnInit(): void {
        this.auth.currentCompany.subscribe((company: any) => {
            if (company && company.currency_symbol) {
                this.currencySymbol = company.currency_symbol;
                this.cdr.detectChanges();
            }
        });

        this.route.paramMap.subscribe(params => {
            this.supplierId = params.get('id');
            if (this.supplierId) {
                this.loadSupplier();
                this.loadStatement();
            } else {
                this.router.navigate(['/purchasing/suppliers']);
            }
        });
    }

    loadSupplier() {
        this.api.get<any>(`/suppliers`).subscribe({
            next: (data) => {
                this.supplier = data.find((s: any) => s.id === this.supplierId);
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.sweetAlert.error('Error', 'No se pudo cargar el proveedor.');
                this.router.navigate(['/purchasing/suppliers']);
            }
        });
    }

    loadStatement() {
        this.isLoadingStatement = true;
        this.api.get<any>(`/suppliers/${this.supplierId}/statement`).subscribe({
            next: (data) => {
                this.statement = data;
                this.isLoadingStatement = false;
                if (this.supplier) {
                    this.supplier.current_balance = data.current_balance;
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
            description: 'Abono a proveedor',
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

        this.api.post(`/suppliers/${this.supplierId}/payments`, paymentData).subscribe({
            next: () => {
                this.sweetAlert.success('Abono registrado', 'El abono al proveedor se registró correctamente.');
                this.isSubmittingPayment = false;
                this.showPaymentModal = false;
                this.cdr.detectChanges();

                // Reload data
                this.loadSupplier();
                this.loadStatement();
            },
            error: (err) => {
                this.isSubmittingPayment = false;
                this.cdr.detectChanges();
                this.sweetAlert.error('Error', err.error?.detail || 'No se pudo registrar el abono.');
            }
        });
    }
}

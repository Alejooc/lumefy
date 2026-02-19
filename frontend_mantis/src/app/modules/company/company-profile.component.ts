import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterModule } from '@angular/router';
import Swal from 'sweetalert2';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

type CompanyProfile = {
  id: string;
  name: string;
  tax_id?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  currency?: string | null;
  currency_symbol?: string | null;
  logo_url?: string | null;
  valid_until?: string | null;
};

@Component({
  selector: 'app-company-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  templateUrl: './company-profile.component.html',
  styleUrl: './company-profile.component.scss'
})
export class CompanyProfileComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private auth = inject(AuthService);

  loading = false;
  saving = false;
  companyValidUntil: string | null = null;

  readonly currencies = [
    { code: 'USD', symbol: '$' },
    { code: 'EUR', symbol: 'EUR' },
    { code: 'COP', symbol: '$' },
    { code: 'MXN', symbol: '$' },
    { code: 'PEN', symbol: 'S/' },
    { code: 'CLP', symbol: '$' }
  ];

  profileForm = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(120)]],
    tax_id: [''],
    address: [''],
    phone: [''],
    email: ['', [Validators.email]],
    website: [''],
    currency: ['USD', [Validators.required]],
    currency_symbol: ['$', [Validators.required, Validators.maxLength(10)]],
    logo_url: ['']
  });

  ngOnInit(): void {
    this.loadCompanyProfile();

    this.profileForm.get('currency')?.valueChanges.subscribe((code) => {
      const currency = this.currencies.find((item) => item.code === code);
      if (currency && !this.profileForm.get('currency_symbol')?.dirty) {
        this.profileForm.patchValue({ currency_symbol: currency.symbol }, { emitEvent: false });
      }
    });
  }

  loadCompanyProfile(): void {
    this.loading = true;
    this.api.get<CompanyProfile>('/companies/me').subscribe({
      next: (company) => {
        this.companyValidUntil = company.valid_until || null; // Store for display
        this.profileForm.patchValue({
          name: company.name ?? '',
          tax_id: company.tax_id ?? '',
          address: company.address ?? '',
          phone: company.phone ?? '',
          email: company.email ?? '',
          website: company.website ?? '',
          currency: company.currency ?? 'USD',
          currency_symbol: company.currency_symbol ?? '$',
          logo_url: company.logo_url ?? ''
        });
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        Swal.fire('Error', err?.error?.detail || 'No se pudo cargar el perfil de empresa.', 'error');
      }
    });
  }

  saveCompanyProfile(): void {
    if (this.profileForm.invalid) {
      this.profileForm.markAllAsTouched();
      return;
    }

    this.saving = true;
    const payload = this.profileForm.getRawValue();

    this.api.put<CompanyProfile>('/companies/me', payload).subscribe({
      next: () => {
        this.auth.fetchCompany().subscribe({
          next: () => {
            this.saving = false;
            Swal.fire('Guardado', 'Perfil de empresa actualizado correctamente.', 'success');
          },
          error: () => {
            this.saving = false;
            Swal.fire('Guardado', 'Perfil guardado. Se actualizaran datos de sesion al recargar.', 'success');
          }
        });
      },
      error: (err) => {
        this.saving = false;
        Swal.fire('Error', err?.error?.detail || 'No se pudo guardar la informacion.', 'error');
      }
    });
  }
}

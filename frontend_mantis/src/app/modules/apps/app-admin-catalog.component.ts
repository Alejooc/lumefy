
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AdminAppDefinition, AppMarketplaceService } from 'src/app/core/services/app-marketplace.service';
import { AuthService } from 'src/app/core/services/auth.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-app-admin-catalog',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './app-admin-catalog.component.html',
  styleUrl: './app-admin-catalog.component.scss'
})
export class AppAdminCatalogComponent implements OnInit {
  private fb = inject(FormBuilder);
  private appService = inject(AppMarketplaceService);
  private auth = inject(AuthService);
  private router = inject(Router);
  private swal = inject(SweetAlertService);

  loading = false;
  apps: AdminAppDefinition[] = [];

  appForm = this.fb.group({
    slug: ['', [Validators.required, Validators.maxLength(80)]],
    name: ['', [Validators.required, Validators.maxLength(120)]],
    description: [''],
    category: ['Integraciones'],
    version: ['1.0.0', [Validators.required]],
    icon: ['appstore'],
    config_schema: ['{}'],
    default_config: ['{}'],
    is_active: [true]
  });

  ngOnInit(): void {
    if (!this.auth.currentUserValue?.is_superuser) {
      this.swal.error('Sin permiso', 'Solo super admin puede crear apps.');
      this.router.navigate(['/dashboard/default']);
      return;
    }
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.appService.adminGetCatalog().subscribe({
      next: (data) => {
        this.apps = data;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        this.swal.error('Error', 'No se pudo cargar el catalogo global.');
      }
    });
  }

  createApp(): void {
    if (this.appForm.invalid) {
      this.appForm.markAllAsTouched();
      return;
    }

    try {
      const payload = {
        ...this.appForm.getRawValue(),
        slug: (this.appForm.get('slug')?.value || '').trim().toLowerCase(),
        config_schema: JSON.parse(this.appForm.get('config_schema')?.value || '{}'),
        default_config: JSON.parse(this.appForm.get('default_config')?.value || '{}')
      };

      this.appService.adminCreateApp(payload).subscribe({
        next: () => {
          this.swal.success('App creada', 'Ya esta disponible para instalar por clientes.');
          this.appForm.patchValue({
            slug: '',
            name: '',
            description: '',
            config_schema: '{}',
            default_config: '{}'
          });
          this.reload();
        },
        error: (err) => {
          this.swal.error('Error', err?.error?.detail || 'No se pudo crear la app.');
        }
      });
    } catch {
      this.swal.error('JSON invalido', 'Revisa config_schema/default_config.');
    }
  }

  toggleActive(app: AdminAppDefinition): void {
    this.appService.adminUpdateApp(app.slug, { is_active: !app.is_active }).subscribe({
      next: () => this.reload(),
      error: (err) => this.swal.error('Error', err?.error?.detail || 'No se pudo actualizar estado.')
    });
  }
}

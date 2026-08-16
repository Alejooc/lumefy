import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { SharedModule } from '../../../theme/shared/shared.module';

interface ProductImportResponse {
  success: boolean;
  count: number;
  products_created?: number;
  products_updated?: number;
  variants_created?: number;
  variants_updated?: number;
  errors?: string[];
}

@Component({
  selector: 'app-product-import',
  templateUrl: './product-import.component.html',
  styleUrls: ['./product-import.component.scss'],
  standalone: true,
  imports: [SharedModule, FormsModule]
})
export class ProductImportComponent {
  file: File | null = null;
  isLoading = false;
  importResult: ProductImportResponse | null = null;

  private apiService = inject(ApiService);
  private swal = inject(SweetAlertService);
  private router = inject(Router);

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file = input.files && input.files.length > 0 ? input.files[0] : null;
    this.importResult = null;
  }

  uploadFile(): void {
    if (!this.file) {
      this.swal.error('Error', 'Por favor selecciona un archivo.');
      return;
    }

    const formData = new FormData();
    formData.append('file', this.file);

    this.isLoading = true;
    this.apiService.post<ProductImportResponse>('/products/import', formData).subscribe({
      next: (response) => {
        this.isLoading = false;
        if (response.success) {
          this.importResult = response;
          const products = (response.products_created || 0) + (response.products_updated || 0);
          const variants = (response.variants_created || 0) + (response.variants_updated || 0);
          this.swal.success(
            'Importación completada',
            `${response.count} fila(s) procesada(s): ${products} producto(s) y ${variants} variante(s).`
          );
          if (response.errors && response.errors.length > 0) {
            this.swal.error('Advertencia', 'Algunas filas tuvieron errores. Revisa el reporte.');
          }
        }
      },
      error: (err: unknown) => {
        this.isLoading = false;
        console.error('Import error', err);
        const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
        this.swal.error('Error', typeof detail === 'string' ? detail : 'Falló la importación del archivo.');
      }
    });
  }

  cancel(): void {
    this.router.navigate(['/products']);
  }
}

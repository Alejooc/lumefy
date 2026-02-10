import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { SharedModule } from '../../../theme/shared/shared.module';

@Component({
    selector: 'app-product-import',
    templateUrl: './product-import.component.html',
    styleUrls: ['./product-import.component.scss'],
    standalone: true,
    imports: [CommonModule, SharedModule, FormsModule]
})
export class ProductImportComponent {
    file: File | null = null;
    isLoading = false;
    importResult: any = null;

    constructor(
        private apiService: ApiService,
        private swal: SweetAlertService,
        private router: Router
    ) { }

    onFileSelected(event: any) {
        this.file = event.target.files[0];
        this.importResult = null;
    }

    uploadFile() {
        if (!this.file) {
            this.swal.error('Error', 'Por favor selecciona un archivo.');
            return;
        }

        const formData = new FormData();
        formData.append('file', this.file);

        this.isLoading = true;
        this.apiService.post<any>('/products/import', formData).subscribe({
            next: (response) => {
                this.isLoading = false;
                if (response.success) {
                    this.importResult = response;
                    this.swal.success('Importación completada', `Se importaron ${response.count} productos correctamente.`);
                    if (response.errors && response.errors.length > 0) {
                        this.swal.error('Advertencia', 'Algunas filas tuvieron errores. Revisa el reporte.');
                    }
                }
            },
            error: (err) => {
                this.isLoading = false;
                console.error('Import error', err);
                this.swal.error('Error', 'Falló la importación del archivo.');
            }
        });
    }

    cancel() {
        this.router.navigate(['/products']);
    }
}

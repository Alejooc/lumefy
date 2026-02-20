import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { LogisticsService, PackageType } from '../logistics.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';

@Component({
    selector: 'app-package-types',
    standalone: true,
    imports: [CommonModule, FormsModule, SharedModule],
    templateUrl: './package-types.component.html',
    styleUrls: ['./package-types.component.scss']
})
export class PackageTypesComponent implements OnInit {
    packageTypes: PackageType[] = [];
    loading = false;
    editMode = false;

    form: Partial<PackageType> = { name: '', width: 0, height: 0, length: 0, max_weight: 0 };
    editingId: string | null = null;

    private logisticsService = inject(LogisticsService);
    private modalService = inject(NgbModal);
    private swal = inject(SweetAlertService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadTypes();
    }

    loadTypes() {
        this.loading = true;
        this.logisticsService.getPackageTypes().subscribe({
            next: (data) => {
                this.packageTypes = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.loading = false;
                this.swal.error('Error', 'No se pudieron cargar los tipos de empaque');
            }
        });
    }

    openModal(content: any, type?: PackageType) {
        if (type) {
            this.editMode = true;
            this.editingId = type.id;
            this.form = { name: type.name, width: type.width, height: type.height, length: type.length, max_weight: type.max_weight };
        } else {
            this.editMode = false;
            this.editingId = null;
            this.form = { name: '', width: 0, height: 0, length: 0, max_weight: 0 };
        }
        this.modalService.open(content, { centered: true });
    }

    save() {
        if (!this.form.name?.trim()) {
            this.swal.error('Error', 'El nombre es requerido');
            return;
        }

        const obs = this.editMode && this.editingId
            ? this.logisticsService.updatePackageType(this.editingId, this.form)
            : this.logisticsService.createPackageType(this.form);

        obs.subscribe({
            next: () => {
                this.modalService.dismissAll();
                this.swal.success('Éxito', this.editMode ? 'Tipo de empaque actualizado' : 'Tipo de empaque creado');
                this.loadTypes();
            },
            error: () => {
                this.swal.error('Error', 'No se pudo guardar');
            }
        });
    }

    deleteType(type: PackageType) {
        this.swal.confirm('¿Eliminar?', `¿Eliminar el tipo de empaque "${type.name}"?`).then((result: any) => {
            if (result.isConfirmed) {
                this.logisticsService.deletePackageType(type.id).subscribe({
                    next: () => {
                        this.swal.success('Eliminado', 'Tipo de empaque eliminado');
                        this.loadTypes();
                    },
                    error: () => {
                        this.swal.error('Error', 'No se pudo eliminar');
                    }
                });
            }
        });
    }

    getDimensions(t: PackageType): string {
        return `${t.width} × ${t.height} × ${t.length} cm`;
    }
}

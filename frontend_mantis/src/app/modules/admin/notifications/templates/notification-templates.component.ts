import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { AdminService } from '../../admin.service';
import Swal from 'sweetalert2';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-notification-templates',
    standalone: true,
    imports: [CommonModule, SharedModule, FormsModule],
    templateUrl: './notification-templates.component.html'
})
export class NotificationTemplatesComponent implements OnInit {
    private adminService = inject(AdminService);
    private modalService = inject(NgbModal);

    templates: any[] = [];
    loading = false;

    selectedTemplate: any = {};

    ngOnInit() {
        this.loadTemplates();
    }

    loadTemplates() {
        this.loading = true;
        this.adminService.getNotificationTemplates().subscribe({
            next: (res) => {
                this.templates = res;
                this.loading = false;
            },
            error: () => this.loading = false
        });
    }

    editTemplate(template: any, content: any) {
        this.selectedTemplate = { ...template }; // Clone
        this.modalService.open(content, { size: 'lg' });
    }

    createTemplate(content: any) {
        this.selectedTemplate = {
            code: '',
            name: '',
            type: 'info',
            title_template: '',
            body_template: '',
            is_active: true
        };
        this.modalService.open(content, { size: 'lg' });
    }

    toggleActive(template: any) {
        template.is_active = !template.is_active;
        this.adminService.updateNotificationTemplate(template.id, { is_active: template.is_active }).subscribe({
            next: () => {
                const status = template.is_active ? 'Activado' : 'Desactivado';
                Swal.fire('Actualizado', `Template ${status}`, 'success');
            },
            error: () => {
                template.is_active = !template.is_active; // Revert
                Swal.fire('Error', 'No se pudo actualizar', 'error');
            }
        });
    }

    saveTemplate() {
        if (this.selectedTemplate.id) {
            this.adminService.updateNotificationTemplate(this.selectedTemplate.id, this.selectedTemplate).subscribe({
                next: (res) => {
                    const index = this.templates.findIndex(t => t.id === res.id);
                    if (index !== -1) this.templates[index] = res;

                    this.modalService.dismissAll();
                    Swal.fire('Guardado', 'Template actualizado correctamente', 'success');
                },
                error: () => Swal.fire('Error', 'No se pudo guardar', 'error')
            });
        } else {
            this.adminService.createNotificationTemplate(this.selectedTemplate).subscribe({
                next: (res) => {
                    this.templates.push(res);
                    this.modalService.dismissAll();
                    Swal.fire('Creado', 'Template creado correctamente', 'success');
                },
                error: (err) => Swal.fire('Error', err.error.detail || 'No se pudo crear', 'error')
            });
        }
    }
}

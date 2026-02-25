import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import Swal from 'sweetalert2';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { AdminService, AdminUser, ManualNotificationPayload } from '../../admin.service';

@Component({
    selector: 'app-send-notification',
    standalone: true,
    imports: [SharedModule, FormsModule],
    templateUrl: './send-notification.component.html'
})
export class SendNotificationComponent implements OnInit {
    private adminService = inject(AdminService);

    loading = false;
    notification: ManualNotificationPayload = {
        target_all: false,
        user_id: null,
        title: '',
        message: '',
        type: 'info',
        link: ''
    };
    users: AdminUser[] = [];

    ngOnInit() {
        this.loadUsers();
    }

    loadUsers() {
        this.adminService.getUsers().subscribe((res) => {
            this.users = res;
        });
    }

    send() {
        if (!this.notification.title || !this.notification.message) {
            Swal.fire('Error', 'Titulo y mensaje son requeridos', 'warning');
            return;
        }

        if (!this.notification.target_all && !this.notification.user_id) {
            Swal.fire('Error', 'Selecciona un usuario o "Enviar a Todos"', 'warning');
            return;
        }

        this.loading = true;
        this.adminService.sendManualNotification(this.notification).subscribe({
            next: (res) => {
                this.loading = false;
                Swal.fire('Enviado', res.message, 'success');
                this.notification = {
                    target_all: false,
                    user_id: null,
                    title: '',
                    message: '',
                    type: 'info',
                    link: ''
                };
            },
            error: () => {
                this.loading = false;
                Swal.fire('Error', 'No se pudo enviar la notificacion', 'error');
            }
        });
    }
}

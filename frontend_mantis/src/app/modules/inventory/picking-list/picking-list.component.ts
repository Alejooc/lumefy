import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-picking-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './picking-list.component.html'
})
export class PickingListComponent implements OnInit {
    tasks: any[] = [];
    loading = false;

    private api = inject(ApiService);

    ngOnInit() {
        this.loadTasks();
    }

    loadTasks() {
        this.loading = true;
        this.api.get<any[]>('/logistics/fulfillment-tasks').subscribe({
            next: (tasks) => {
                this.tasks = tasks.filter(task => ['OPEN', 'IN_PROGRESS'].includes(task.status));
                this.loading = false;
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
            }
        });
    }

    startTask(task: any) {
        Swal.fire({
            title: '¿Iniciar picking?',
            text: 'La orden pasará a preparación.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, iniciar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            if (result.isConfirmed) {
                this.api.post(`/logistics/fulfillment-tasks/${task.id}/start`).subscribe({
                    next: () => {
                        Swal.fire('Picking iniciado', 'Registra las unidades preparadas en el detalle de la orden.', 'success');
                        this.loadTasks();
                    },
                    error: (err) => {
                        Swal.fire('Error', 'No se pudo actualizar: ' + err.message, 'error');
                    }
                });
            }
        });
    }

    completeTask(task: any) {
        this.api.post(`/logistics/fulfillment-tasks/${task.id}/complete`).subscribe({
            next: () => { Swal.fire('Picking finalizado', 'La orden pasó a empaque.', 'success'); this.loadTasks(); },
            error: (err) => Swal.fire('No se puede finalizar', err.error?.detail || err.message, 'error')
        });
    }
}

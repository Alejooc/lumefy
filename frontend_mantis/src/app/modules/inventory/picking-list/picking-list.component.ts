import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import Swal from 'sweetalert2';

interface FulfillmentTask {
    id: string;
    sale_id: string;
    status: 'OPEN' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
    warehouse_name: string;
    created_at: string | null;
    sale: { id: string; client_name: string; item_count: number };
}

type ApiError = { message?: string; error?: { detail?: string } };

@Component({
    selector: 'app-picking-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './picking-list.component.html'
})
export class PickingListComponent implements OnInit {
    tasks: FulfillmentTask[] = [];
    loading = false;

    private api = inject(ApiService);

    ngOnInit() {
        this.loadTasks();
    }

    loadTasks() {
        this.loading = true;
        this.api.get<FulfillmentTask[]>('/logistics/fulfillment-tasks').subscribe({
            next: (tasks) => {
                this.tasks = tasks.filter(task => ['OPEN', 'IN_PROGRESS'].includes(task.status));
                this.loading = false;
            },
            error: (err: unknown) => {
                console.error(err);
                this.loading = false;
            }
        });
    }

    startTask(task: FulfillmentTask) {
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
                    error: (err: unknown) => {
                        const apiError = err as ApiError;
                        Swal.fire('Error', 'No se pudo actualizar: ' + (apiError.error?.detail || apiError.message || 'Intenta de nuevo.'), 'error');
                    }
                });
            }
        });
    }

    completeTask(task: FulfillmentTask) {
        this.api.post(`/logistics/fulfillment-tasks/${task.id}/complete`).subscribe({
            next: () => { Swal.fire('Picking finalizado', 'La orden pasó a empaque.', 'success'); this.loadTasks(); },
            error: (err: unknown) => {
                const apiError = err as ApiError;
                Swal.fire('No se puede finalizar', apiError.error?.detail || apiError.message || 'Intenta de nuevo.', 'error');
            }
        });
    }
}

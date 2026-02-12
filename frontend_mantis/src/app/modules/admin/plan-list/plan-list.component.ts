import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { PlanService, Plan } from '../plan.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-plan-list',
    standalone: true,
    imports: [CommonModule, RouterModule, SharedModule],
    templateUrl: './plan-list.component.html'
})
export class PlanListComponent implements OnInit {
    plans: Plan[] = [];
    loading = false;

    private planService = inject(PlanService);
    private cdr = inject(ChangeDetectorRef);

    ngOnInit() {
        this.loadPlans();
    }

    loadPlans() {
        this.loading = true;
        this.planService.getAllPlans().subscribe({
            next: (data) => {
                this.plans = data;
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudieron cargar los planes', 'error');
            }
        });
    }

    toggleStatus(plan: Plan) {
        // Implement toggle logic
        const newStatus = !plan.is_active;
        this.planService.updatePlan(plan.id, { is_active: newStatus }).subscribe({
            next: () => {
                plan.is_active = newStatus;
                this.cdr.detectChanges();
            },
            error: () => Swal.fire('Error', 'No se pudo actualizar', 'error')
        });
    }
}

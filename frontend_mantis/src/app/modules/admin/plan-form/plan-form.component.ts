import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, FormArray, FormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterModule } from '@angular/router';
import { PlanService } from '../plan.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-plan-form',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, RouterModule, SharedModule, FormsModule], // SharedModule likely exports CardComponent etc.
    templateUrl: './plan-form.component.html'
})
export class PlanFormComponent implements OnInit {
    planForm: FormGroup;
    loading = false;
    isEditing = false;
    planId: string | null = null;

    private fb = inject(FormBuilder);
    private planService = inject(PlanService);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private cdr = inject(ChangeDetectorRef);

    // Dynamic Features List
    featuresList: string[] = [];
    newFeatureText: string = '';

    constructor() {
        this.planForm = this.fb.group({
            name: ['', Validators.required],
            code: ['', Validators.required],
            description: [''],
            price: [0, [Validators.required, Validators.min(0)]],
            currency: ['USD', Validators.required],
            duration_days: [30, [Validators.required, Validators.min(1)]],
            is_active: [true],
            is_public: [true],
            // Limits
            limit_users: [5, Validators.required],
            limit_storage: [1000, Validators.required], // MB
            limit_branches: [1, Validators.required]
        });
    }

    ngOnInit() {
        this.route.paramMap.subscribe(params => {
            const id = params.get('id');
            if (id) {
                this.isEditing = true;
                this.planId = id;
                this.loadPlan(id);
            }
        });
    }

    loadPlan(id: string) {
        this.loading = true;
        this.planService.getAllPlans().subscribe(plans => {
            const plan = plans.find(p => p.id === id);
            if (plan) {
                this.planForm.patchValue({
                    name: plan.name,
                    code: plan.code,
                    description: plan.description,
                    price: plan.price,
                    currency: plan.currency,
                    duration_days: plan.duration_days,
                    is_active: plan.is_active,
                    is_public: plan.is_public,
                    limit_users: plan.limits?.users || 0,
                    limit_storage: plan.limits?.storage || 0,
                    limit_branches: plan.limits?.branches || 1
                });

                // Load Features (Handle Legacy Dict vs New Array)
                this.featuresList = [];
                if (plan.features) {
                    if (Array.isArray(plan.features)) {
                        this.featuresList = plan.features;
                    } else if (typeof plan.features === 'object') {
                        // Convert legacy dict keys to list
                        this.featuresList = Object.keys(plan.features);
                    }
                }

                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    addFeature() {
        if (this.newFeatureText.trim()) {
            this.featuresList.push(this.newFeatureText.trim());
            this.newFeatureText = '';
        }
    }

    removeFeature(index: number) {
        this.featuresList.splice(index, 1);
    }

    // Capture enter key in input to prevent submit and add feature instead
    onFeatureKeydown(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            event.preventDefault();
            this.addFeature();
        }
    }

    onSubmit() {
        if (this.planForm.invalid) return;

        this.loading = true;
        const formVal = this.planForm.value;

        // Transform limits back to dict
        const limits = {
            users: formVal.limit_users,
            storage: formVal.limit_storage,
            branches: formVal.limit_branches
        };

        const payload = {
            ...formVal,
            limits: limits,
            features: this.featuresList // Send simple list of strings
        };
        // Remove flat limit fields
        delete payload.limit_users;
        delete payload.limit_storage;
        delete payload.limit_branches;

        const request$ = this.isEditing && this.planId
            ? this.planService.updatePlan(this.planId, payload)
            : this.planService.createPlan(payload);

        request$.subscribe({
            next: () => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Guardado', 'Plan guardado exitosamente', 'success').then(() => {
                    this.router.navigate(['/admin/plans']);
                });
            },
            error: (err) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo guardar: ' + (err.error?.detail || err.message), 'error');
            }
        });
    }
}

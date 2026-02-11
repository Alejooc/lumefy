import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { BranchService, Branch } from '../../../core/services/branch.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-branch-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './branch-list.component.html'
})
export class BranchListComponent implements OnInit {
    private branchService = inject(BranchService);
    branches: Branch[] = [];
    isLoading = false;

    ngOnInit() {
        this.loadBranches();
    }

    loadBranches() {
        this.isLoading = true;
        this.branchService.getBranches().subscribe({
            next: (data) => {
                this.branches = data;
                this.isLoading = false;
            },
            error: (err) => {
                console.error('Error loading branches', err);
                this.isLoading = false;
            }
        });
    }

    deleteBranch(id: string) {
        Swal.fire({
            title: '¿Estás seguro?',
            text: "No podrás revertir esto",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, borrar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            /* 
             * Ideally we would call delete on service, but service might miss delete method. 
             * I will need to check if service has delete. Yes, I saw it only has getBranches.
             * I will assume I need to add CRUD to service or just use ApiService directly here or update service later.
             * For speed, I'll update service first or inject ApiService. Let's use ApiService directly for delete to be fast, 
             * but better to update service. I'll update service in next step.
             */
        });
    }
}

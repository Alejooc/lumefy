import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Branch, BranchService } from '../../../core/services/branch.service';

@Component({
    selector: 'app-branch-list',
    standalone: true,
    imports: [CommonModule, RouterModule],
    templateUrl: './branch-list.component.html'
})
export class BranchListComponent implements OnInit {
    private branchService = inject(BranchService);
    private cdr = inject(ChangeDetectorRef);

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
                this.cdr.detectChanges();
            },
            error: (error: unknown) => {
                console.error('Error loading branches', error);
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }
}

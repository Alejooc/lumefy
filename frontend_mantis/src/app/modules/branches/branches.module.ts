import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { BranchesRoutingModule } from './branches-routing.module';
import { BranchListComponent } from './branch-list/branch-list.component';
import { BranchFormComponent } from './branch-form/branch-form.component';

@NgModule({
    imports: [
        CommonModule,
        ReactiveFormsModule,
        BranchesRoutingModule,
        BranchListComponent,
        BranchFormComponent
    ]
})
export class BranchesModule { }

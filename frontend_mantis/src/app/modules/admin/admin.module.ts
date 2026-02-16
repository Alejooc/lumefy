import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgApexchartsModule } from 'ng-apexcharts';

import { CompanyListComponent } from './company-list/company-list.component';
import { CompanyFormComponent } from './company-form/company-form.component';
import { AdminDashboardComponent } from './dashboard/admin-dashboard.component';
import { PlanListComponent } from './plan-list/plan-list.component';
import { PlanFormComponent } from './plan-form/plan-form.component';
import { AdminSettingsComponent } from './settings/admin-settings.component';
import { AdminUserListComponent } from './user-list/admin-user-list.component';
import { SharedModule } from '../../theme/shared/shared.module';

const routes: Routes = [
    {
        path: '',
        children: [
            { path: 'dashboard', component: AdminDashboardComponent },
            { path: 'companies', component: CompanyListComponent },
            { path: 'companies/new', component: CompanyFormComponent },
            { path: 'companies/edit/:id', component: CompanyFormComponent },
            { path: 'plans', component: PlanListComponent },
            { path: 'plans/new', component: PlanFormComponent },
            { path: 'plans/edit/:id', component: PlanFormComponent },
            { path: 'users', component: AdminUserListComponent },
            { path: 'settings', component: AdminSettingsComponent },
            { path: '', redirectTo: 'dashboard', pathMatch: 'full' }
        ]
    }
];

@NgModule({
    declarations: [CompanyListComponent, CompanyFormComponent],
    imports: [
        CommonModule,
        SharedModule,
        FormsModule,
        ReactiveFormsModule,
        RouterModule.forChild(routes),
        NgApexchartsModule,
        AdminDashboardComponent,
        PlanListComponent,
        PlanFormComponent,
        AdminSettingsComponent
    ]
})
export class AdminModule { }

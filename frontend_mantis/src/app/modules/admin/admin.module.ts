import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Routes } from '@angular/router';
import { CompanyListComponent } from './company-list/company-list.component';
import { CompanyFormComponent } from './company-form/company-form.component';
import { SharedModule } from '../../theme/shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

const routes: Routes = [
    {
        path: '',
        children: [
            { path: 'companies', component: CompanyListComponent },
            { path: 'companies/new', component: CompanyFormComponent },
            { path: 'companies/edit/:id', component: CompanyFormComponent }
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
        RouterModule.forChild(routes)
    ]
})
export class AdminModule { }

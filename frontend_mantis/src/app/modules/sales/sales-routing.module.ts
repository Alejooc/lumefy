import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { SalesListComponent } from './sales-list/sales-list.component';
import { SalesFormComponent } from './sales-form/sales-form.component';
import { SalesViewComponent } from './sales-view/sales-view.component';

const routes: Routes = [
    {
        path: '',
        children: [
            { path: '', component: SalesListComponent },
            { path: 'quote', component: SalesFormComponent }, // Create Quote
            { path: 'order', component: SalesFormComponent }, // Create Order directly?
            { path: 'edit/:id', component: SalesFormComponent },
            { path: 'view/:id', component: SalesViewComponent }
        ]
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class SalesRoutingModule { }

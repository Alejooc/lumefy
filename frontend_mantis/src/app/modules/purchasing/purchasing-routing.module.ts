import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { SupplierListComponent } from './supplier-list/supplier-list.component';
import { SupplierFormComponent } from './supplier-form/supplier-form.component';
import { PurchaseListComponent } from './purchase-list/purchase-list.component';
import { PurchaseFormComponent } from './purchase-form/purchase-form.component';
import { PurchaseViewComponent } from './purchase-view/purchase-view.component';
import { PriceListListComponent } from './pricelist-list/pricelist-list.component';
import { PriceListFormComponent } from './pricelist-form/pricelist-form.component';

const routes: Routes = [
    {
        path: '',
        children: [
            {
                path: 'suppliers',
                component: SupplierListComponent
            },
            {
                path: 'suppliers/add',
                component: SupplierFormComponent
            },
            {
                path: 'suppliers/edit/:id',
                component: SupplierFormComponent
            },
            {
                path: 'orders',
                component: PurchaseListComponent
            },
            {
                path: 'orders/add',
                component: PurchaseFormComponent
            },
            {
                path: 'orders/view/:id',
                component: PurchaseViewComponent
            },
            {
                path: 'pricelists',
                component: PriceListListComponent
            },
            {
                path: 'pricelists/add',
                component: PriceListFormComponent
            },
            {
                path: 'pricelists/edit/:id',
                component: PriceListFormComponent
            }
        ]
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class PurchasingRoutingModule { }

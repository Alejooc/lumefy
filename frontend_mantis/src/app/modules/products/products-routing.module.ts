import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { ProductListComponent } from './product-list/product-list.component';
import { ProductImportComponent } from './product-import/product-import.component';
import { ProductFormComponent } from './product-form/product-form.component';

const routes: Routes = [
    {
        path: '',
        component: ProductListComponent
    },
    {
        path: 'create',
        component: ProductFormComponent
    },
    {
        path: 'edit/:id',
        component: ProductFormComponent
    },
    {
        path: 'import',
        component: ProductImportComponent
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class ProductsRoutingModule { }

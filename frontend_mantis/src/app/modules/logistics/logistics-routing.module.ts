import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PickingComponent } from './picking/picking.component';
import { PackingComponent } from './packing/packing.component';

const routes: Routes = [
    {
        path: 'picking/:id',
        component: PickingComponent
    },
    {
        path: 'packing/:id',
        component: PackingComponent
    },
    {
        path: 'package-types',
        loadComponent: () => import('./package-types/package-types.component').then(m => m.PackageTypesComponent)
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class LogisticsRoutingModule { }

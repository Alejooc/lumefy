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
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class LogisticsRoutingModule { }

import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { InventoryListComponent } from './inventory-list/inventory-list.component';

import { InventoryMovementComponent } from './inventory-movement/inventory-movement.component';
import { InventoryHistoryComponent } from './inventory-history/inventory-history.component';

const routes: Routes = [
    {
        path: '',
        component: InventoryListComponent
    },
    {
        path: 'movement',
        component: InventoryMovementComponent
    },
    {
        path: 'history/:productId',
        component: InventoryHistoryComponent
    },
    {
        path: 'picking',
        loadComponent: () => import('./picking-list/picking-list.component').then(m => m.PickingListComponent)
    },
    {
        path: 'picking/print/:id',
        loadComponent: () => import('./picking-print/picking-print.component').then(m => m.PickingPrintComponent)
    },
    {
        path: 'stock-take',
        loadComponent: () => import('./stock-take-list/stock-take-list.component').then(m => m.StockTakeListComponent)
    },
    {
        path: 'stock-take/:id',
        loadComponent: () => import('./stock-take-form/stock-take-form.component').then(m => m.StockTakeFormComponent)
    },
    {
        path: 'logistics-board',
        loadComponent: () => import('./logistics-board/logistics-board.component').then(m => m.LogisticsBoardComponent)
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class InventoryRoutingModule { }

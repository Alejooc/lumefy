import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { InventoryRoutingModule } from './inventory-routing.module';
import { InventoryListComponent } from './inventory-list/inventory-list.component';
import { SharedModule } from '../../theme/shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

import { InventoryMovementComponent } from './inventory-movement/inventory-movement.component';
import { InventoryHistoryComponent } from './inventory-history/inventory-history.component';

@NgModule({
    declarations: [
        InventoryListComponent
    ],
    imports: [
        CommonModule,
        InventoryRoutingModule,
        SharedModule,
        FormsModule,
        ReactiveFormsModule,
        InventoryMovementComponent,
        InventoryHistoryComponent
    ]
})
export class InventoryModule { }

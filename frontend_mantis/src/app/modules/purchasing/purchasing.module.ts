import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { PurchasingRoutingModule } from './purchasing-routing.module';
// Import standalone components if needed here, but since they are standalone, 
// they are imported in routing implicitly or via lazy loading if configured that way.
// However, typically in non-standalone app structure, we might declare them.
// But earlier components were standalone: true. So we don't declare them.
// Just imports.

@NgModule({
  declarations: [],
  imports: [
    CommonModule,
    PurchasingRoutingModule
  ]
})
export class PurchasingModule { }

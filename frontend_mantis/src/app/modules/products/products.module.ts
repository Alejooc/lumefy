import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { ProductsRoutingModule } from './products-routing.module';
import { ProductListComponent } from './product-list/product-list.component';
import { SharedModule } from '../../theme/shared/shared.module';

import { ProductImportComponent } from './product-import/product-import.component';

@NgModule({
    declarations: [
        ProductListComponent
    ],
    imports: [
        CommonModule,
        FormsModule,
        ProductsRoutingModule,
        SharedModule,
        ProductImportComponent
    ]
})
export class ProductsModule { }


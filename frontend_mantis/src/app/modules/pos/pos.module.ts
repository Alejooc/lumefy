import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { PosRoutingModule } from './pos-routing.module';
import { PosComponent } from './pos.component';
import { SharedModule } from '../../theme/shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgSelectModule } from '@ng-select/ng-select';

@NgModule({
    declarations: [
        PosComponent
    ],
    imports: [
        CommonModule,
        PosRoutingModule,
        SharedModule,
        FormsModule,
        ReactiveFormsModule,
        NgSelectModule
    ]
})
export class PosModule { }

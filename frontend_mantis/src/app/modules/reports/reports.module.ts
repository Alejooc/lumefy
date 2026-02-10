import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReportsRoutingModule } from './reports-routing.module';
import { ReportsComponent } from './reports.component';
import { SharedModule } from '../../theme/shared/shared.module';
import { NgApexchartsModule } from 'ng-apexcharts';

@NgModule({
    declarations: [
        ReportsComponent
    ],
    imports: [
        CommonModule,
        ReportsRoutingModule,
        SharedModule,
        NgApexchartsModule
    ]
})
export class ReportsModule { }

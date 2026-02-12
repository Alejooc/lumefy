import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { NgbTooltipModule, NgbNavModule } from '@ng-bootstrap/ng-bootstrap';

import { LogisticsRoutingModule } from './logistics-routing.module';

@NgModule({
    imports: [
        CommonModule,
        LogisticsRoutingModule
    ]
})
export class LogisticsModule { }

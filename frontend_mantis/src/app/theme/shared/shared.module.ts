import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';

// project import
import { CardComponent } from './components/card/card.component';

// third party
import { NgScrollbarModule } from 'ngx-scrollbar';
import { IconDirective } from '@ant-design/icons-angular';
import { NgSelectModule } from '@ng-select/ng-select';

// bootstrap import
import {
  NgbDropdownModule,
  NgbNavModule,
  NgbTooltipModule,
  NgbModule,
  NgbAccordionModule,
  NgbCollapseModule,
  NgbDatepickerModule
} from '@ng-bootstrap/ng-bootstrap';

import { HasPermissionDirective } from './directives/has-permission.directive';

import { RouterModule } from '@angular/router';

@NgModule({
  declarations: [],
  imports: [
    RouterModule,
    HasPermissionDirective,
    CommonModule,
    NgbDropdownModule,
    NgbNavModule,
    NgbTooltipModule,
    NgbModule,
    NgbAccordionModule,
    NgbCollapseModule,
    NgbDatepickerModule,
    NgScrollbarModule,
    FormsModule,
    ReactiveFormsModule,
    CardComponent,
    NgSelectModule,
    IconDirective
  ],
  exports: [
    RouterModule,
    CommonModule,
    NgbDropdownModule,
    NgbNavModule,
    NgbTooltipModule,
    NgbModule,
    NgbAccordionModule,
    NgbCollapseModule,
    NgbDatepickerModule,
    NgScrollbarModule,
    NgSelectModule,
    FormsModule,
    ReactiveFormsModule,
    CardComponent,
    IconDirective,
    HasPermissionDirective
  ]
})
export class SharedModule { }

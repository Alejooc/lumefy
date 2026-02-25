import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { SharedModule } from '../../theme/shared/shared.module';

import { ProfileRoutingModule } from './profile-routing.module';

@NgModule({
    imports: [
        CommonModule,
        ProfileRoutingModule,
        SharedModule,
        FormsModule,
        ReactiveFormsModule
    ]
})
export class ProfileModule { }

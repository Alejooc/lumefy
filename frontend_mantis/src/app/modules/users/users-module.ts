import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { UsersRoutingModule } from './users-routing-module';
import { UserListComponent } from './user-list/user-list';
import { UserFormComponent } from './user-form/user-form';
import { RoleManagementComponent } from './role-management/role-management.component';
import { SharedModule } from '../../theme/shared/shared.module';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';


@NgModule({
  declarations: [
    UserListComponent,
    UserFormComponent,
    RoleManagementComponent
  ],
  imports: [
    CommonModule,
    UsersRoutingModule,
    SharedModule,
    FormsModule,
    ReactiveFormsModule
  ]
})
export class UsersModule { }

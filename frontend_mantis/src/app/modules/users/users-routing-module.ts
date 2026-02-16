import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { UserListComponent } from './user-list/user-list';
import { UserFormComponent } from './user-form/user-form';
import { RoleManagementComponent } from './role-management/role-management.component';

const routes: Routes = [
  { path: '', component: UserListComponent },
  { path: 'roles', component: RoleManagementComponent },
  { path: 'new', component: UserFormComponent },
  { path: 'edit/:id', component: UserFormComponent }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class UsersRoutingModule { }

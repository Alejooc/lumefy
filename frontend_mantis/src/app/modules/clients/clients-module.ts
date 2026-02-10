import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormsModule } from '@angular/forms'; // Ensure FormsModule and Reactive are here
import { ClientsRoutingModule } from './clients-routing-module';
import { ClientListComponent } from './client-list/client-list';
import { ClientFormComponent } from './client-form/client-form';
import { ClientService } from './client.service';
import { SharedModule } from '../../theme/shared/shared.module';

@NgModule({
  declarations: [
    ClientListComponent,
    ClientFormComponent
  ],
  imports: [
    CommonModule,
    ClientsRoutingModule,
    SharedModule,
    ReactiveFormsModule,
    FormsModule
  ],
  providers: [
    ClientService
  ]
})
export class ClientsModule { }

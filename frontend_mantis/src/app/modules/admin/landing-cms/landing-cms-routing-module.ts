import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LandingCmsComponent } from './landing-cms/landing-cms';

const routes: Routes = [
  {
    path: '',
    component: LandingCmsComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class LandingCmsRoutingModule { }

// angular import
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// Project import
import { AdminLayout } from './theme/layouts/admin-layout/admin-layout.component';
import { GuestLayoutComponent } from './theme/layouts/guest-layout/guest-layout.component';
import { AuthGuard } from './core/auth.guard';
import { GuestGuard } from './core/guest.guard';
import { SuperuserGuard } from './core/superuser.guard';

const routes: Routes = [
  {
    path: '',
    component: GuestLayoutComponent,
    canActivate: [GuestGuard],
    children: [
      {
        path: '',
        pathMatch: 'full',
        redirectTo: 'login'
      },
      {
        path: 'login',
        loadComponent: () => import('./demo/pages/authentication/auth-login/auth-login.component').then((c) => c.AuthLoginComponent)
      },
      {
        path: 'register',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-register/auth-register.component').then((c) => c.AuthRegisterComponent)
      }
    ]
  },
  {
    path: '',
    component: AdminLayout,
    canActivate: [AuthGuard],
    children: [
      {
        path: 'dashboard/default',
        loadComponent: () => import('./demo/dashboard/default/default.component').then((c) => c.DefaultComponent)
      },
      {
        path: 'typography',
        loadComponent: () => import('./demo/component/basic-component/typography/typography.component').then((c) => c.TypographyComponent)
      },
      {
        path: 'color',
        loadComponent: () => import('./demo/component/basic-component/color/color.component').then((c) => c.ColorComponent)
      },
      {
        path: 'management/branches',
        loadChildren: () => import('./modules/branches/branches.module').then(m => m.BranchesModule)
      },
      {
        path: 'branches',
        loadChildren: () => import('./modules/branches/branches.module').then(m => m.BranchesModule)
      },
      {
        path: 'sample-page',
        loadComponent: () => import('./demo/others/sample-page/sample-page.component').then((c) => c.SamplePageComponent)
      },
      {
        path: 'products',
        loadChildren: () => import('./modules/products/products.module').then((m) => m.ProductsModule)
      },
      {
        path: 'categories',
        loadChildren: () => import('./modules/categories/categories.module').then((m) => m.CategoriesModule)
      },
      {
        path: 'inventory',
        loadChildren: () => import('./modules/inventory/inventory.module').then((m) => m.InventoryModule)
      },
      {
        path: 'pos',
        loadChildren: () => import('./modules/pos/pos.module').then((m) => m.PosModule)
      },
      {
        path: 'reports',
        loadChildren: () => import('./modules/reports/reports.module').then((m) => m.ReportsModule)
      },
      {
        path: 'clients',
        loadChildren: () => import('./modules/clients/clients-module').then((m) => m.ClientsModule)
      },
      {
        path: 'users',
        loadChildren: () => import('./modules/users/users-module').then((m) => m.UsersModule)
      },
      {
        path: 'purchasing',
        loadChildren: () => import('./modules/purchasing/purchasing.module').then(m => m.PurchasingModule)
      },
      {
        path: 'sales',
        loadChildren: () => import('./modules/sales/sales.module').then(m => m.SalesModule)
      },
      {
        path: 'logistics',
        loadChildren: () => import('./modules/logistics/logistics.module').then((m) => m.LogisticsModule)
      },
      {
        path: 'audit',
        loadComponent: () => import('./modules/audit/audit-list/audit-list.component').then((m) => m.AuditListComponent)
      },
      {
        path: 'admin',
        canActivate: [SuperuserGuard],
        loadChildren: () => import('./modules/admin/admin.module').then(m => m.AdminModule)
      },
      {
        path: 'brands',
        loadComponent: () => import('./modules/brands/brand-list.component').then(c => c.BrandListComponent)
      },
      {
        path: 'units-of-measure',
        loadComponent: () => import('./modules/units-of-measure/uom-list.component').then(c => c.UomListComponent)
      },
      {
        path: 'company/profile',
        loadComponent: () => import('./modules/company/company-profile.component').then(c => c.CompanyProfileComponent)
      }
    ]
  },
  {
    path: '**',
    redirectTo: 'login'
  }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }

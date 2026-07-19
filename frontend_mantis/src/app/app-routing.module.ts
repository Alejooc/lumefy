// angular import
import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

// Project import
import { AdminLayout } from './theme/layouts/admin-layout/admin-layout.component';
import { GuestLayoutComponent } from './theme/layouts/guest-layout/guest-layout.component';
import { LandingLayout } from './theme/layouts/landing-layout/landing-layout';
import { AuthGuard } from './core/auth.guard';
import { GuestGuard } from './core/guest.guard';
import { SuperuserGuard } from './core/superuser.guard';
import { TenantGuard } from './core/tenant.guard';
import { PosAccessGuard } from './core/pos-access.guard';
import { AppAccessGuard } from './core/app-access.guard';

const routes: Routes = [
  {
    path: '',
    component: LandingLayout,
    children: [
      {
        path: '',
        loadChildren: () => import('./demo/pages/landing/landing-module').then(m => m.LandingModule)
      }
    ]
  },
  {
    path: '',
    component: GuestLayoutComponent,
    canActivate: [GuestGuard],
    children: [
      {
        path: 'login',
        loadComponent: () => import('./demo/pages/authentication/auth-login/auth-login.component').then((c) => c.AuthLoginComponent)
      },
      {
        path: 'forgot-password',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-forgot-password/auth-forgot-password.component').then((c) => c.AuthForgotPasswordComponent)
      },
      {
        path: 'reset-password',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-reset-password/auth-reset-password.component').then((c) => c.AuthResetPasswordComponent)
      },
      {
        path: 'register',
        loadComponent: () =>
          import('./demo/pages/authentication/auth-register/auth-register.component').then((c) => c.AuthRegisterComponent)
      }
    ]
  },
  {
    path: 'pos',
    canActivate: [AuthGuard, TenantGuard, PosAccessGuard],
    loadComponent: () => import('./modules/pos/pos.component').then((c) => c.PosComponent)
  },
  {
    path: '',
    component: AdminLayout,
    canActivate: [AuthGuard],
    children: [
      {
        path: 'dashboard',
        redirectTo: 'dashboard/default',
        pathMatch: 'full'
      },
      {
        path: 'dashboard/default',
        canActivate: [TenantGuard],
        loadComponent: () => import('./demo/dashboard/default/default.component').then((c) => c.DefaultComponent)
      },
      {
        path: 'management/branches',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/branches/branches.module').then(m => m.BranchesModule)
      },
      {
        path: 'branches',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/branches/branches.module').then(m => m.BranchesModule)
      },
      {
        path: 'products',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/products/products.module').then((m) => m.ProductsModule)
      },
      {
        path: 'categories',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/categories/categories.module').then((m) => m.CategoriesModule)
      },
      {
        path: 'inventory',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/inventory/inventory.module').then((m) => m.InventoryModule)
      },
      {
        path: 'reports',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/reports/reports.module').then((m) => m.ReportsModule)
      },
      {
        path: 'clients',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/clients/clients-module').then((m) => m.ClientsModule)
      },
      {
        path: 'crm',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/crm/crm-pipeline.component').then((c) => c.CrmPipelineComponent)
      },
      { path: 'manufacturing', canActivate: [TenantGuard], loadComponent: () => import('./modules/manufacturing/manufacturing.component').then(c => c.ManufacturingComponent) },
      {
        path: 'users',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/users/users-module').then((m) => m.UsersModule)
      },
      {
        path: 'purchasing',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/purchasing/purchasing.module').then(m => m.PurchasingModule)
      },
      {
        path: 'sales',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/sales/sales.module').then(m => m.SalesModule)
      },
      {
        path: 'returns',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/returns/returns.routes').then(m => m.routes)
      },
      {
        path: 'invoices',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/invoices/invoice-list.component').then(c => c.InvoiceListComponent)
      },
      {
        path: 'logistics',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/logistics/logistics.module').then((m) => m.LogisticsModule)
      },
      {
        path: 'audit',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/audit/audit-list/audit-list.component').then((m) => m.AuditListComponent)
      },
      {
        path: 'admin',
        canActivate: [SuperuserGuard],
        loadChildren: () => import('./modules/admin/admin.module').then(m => m.AdminModule)
      },
      {
        path: 'brands',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/brands/brand-list.component').then(c => c.BrandListComponent)
      },
      {
        path: 'units-of-measure',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/units-of-measure/uom-list.component').then(c => c.UomListComponent)
      },
      {
        path: 'company/profile',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/company/company-profile.component').then(c => c.CompanyProfileComponent)
      },
      {
        path: 'settings/health',
        canActivate: [SuperuserGuard],
        loadComponent: () => import('./modules/settings/system-health.component').then((c) => c.SystemHealthComponent)
      },
      {
        path: 'settings/database',
        canActivate: [SuperuserGuard],
        loadComponent: () => import('./modules/settings/database-stats/database-stats.component').then((c) => c.DatabaseStatsComponent)
      },
      {
        path: 'profile',
        loadChildren: () => import('./modules/profile/profile.module').then(m => m.ProfileModule)
      },
      {
        path: 'billing',
        canActivate: [TenantGuard],
        loadChildren: () => import('./modules/billing/billing.module').then(m => m.BillingModule)
      },
      {
        path: 'apps/store',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/apps/app-store.component').then((c) => c.AppStoreComponent)
      },
      {
        path: 'apps/installed/:slug',
        canActivate: [TenantGuard],
        loadComponent: () => import('./modules/apps/app-installed-detail.component').then((c) => c.AppInstalledDetailComponent)
      },
      {
        path: 'apps/admin',
        canActivate: [SuperuserGuard],
        loadComponent: () => import('./modules/apps/app-admin-catalog.component').then((c) => c.AppAdminCatalogComponent)
      },
      {
        path: 'commerce',
        canActivate: [TenantGuard, AppAccessGuard],
        data: { appSlug: 'ecommerce', requiredPermission: 'manage_company' },
        loadChildren: () => import('./modules/apps/ecommerce.routes').then((m) => m.routes)
      },
      {
        path: 'apps/ecommerce',
        canActivate: [TenantGuard, AppAccessGuard],
        data: { appSlug: 'ecommerce', requiredPermission: 'manage_company' },
        loadChildren: () => import('./modules/apps/ecommerce.routes').then((m) => m.routes)
      },
      {
        path: '**',
        loadComponent: () => import('./demo/pages/not-found/not-found.component').then((c) => c.NotFoundComponent)
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

import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./ecommerce/ecommerce-shell.component').then((c) => c.EcommerceShellComponent),
    children: [
      {
        path: '',
        loadComponent: () => import('./ecommerce/ecommerce-overview.component').then((c) => c.EcommerceOverviewComponent)
      },
      {
        path: 'settings',
        loadComponent: () => import('./ecommerce/ecommerce-settings.component').then((c) => c.EcommerceSettingsComponent)
      },
      {
        path: 'store',
        loadComponent: () => import('./ecommerce/ecommerce-settings.component').then((c) => c.EcommerceSettingsComponent)
      },
      {
        path: 'branding',
        loadComponent: () => import('./ecommerce/ecommerce-branding.component').then((c) => c.EcommerceBrandingComponent)
      },
      {
        path: 'home',
        loadComponent: () => import('./ecommerce/ecommerce-home.component').then((c) => c.EcommerceHomeComponent)
      },
      {
        path: 'design',
        loadComponent: () => import('./ecommerce/ecommerce-home.component').then((c) => c.EcommerceHomeComponent)
      },
      {
        path: 'checkout',
        loadComponent: () => import('./ecommerce/ecommerce-checkout.component').then((c) => c.EcommerceCheckoutComponent)
      },
      {
        path: 'seo',
        loadComponent: () => import('./ecommerce/ecommerce-seo.component').then((c) => c.EcommerceSeoComponent)
      },
      {
        path: 'collections',
        loadComponent: () => import('./ecommerce/ecommerce-collections.component').then((c) => c.EcommerceCollectionsComponent)
      },
      {
        path: 'navigation',
        loadComponent: () => import('./ecommerce/ecommerce-navigation.component').then((c) => c.EcommerceNavigationComponent)
      },
      {
        path: 'payments',
        loadComponent: () => import('./ecommerce/ecommerce-payments.component').then((c) => c.EcommercePaymentsComponent)
      }
    ]
  }
];

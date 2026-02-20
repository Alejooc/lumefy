import { Routes } from '@angular/router';

export const routes: Routes = [
    {
        path: '',
        loadComponent: () => import('./return-list/return-list.component').then(c => c.ReturnListComponent)
    },
    {
        path: 'new',
        loadComponent: () => import('./return-form/return-form.component').then(c => c.ReturnFormComponent)
    },
    {
        path: 'view/:id',
        loadComponent: () => import('./return-view/return-view.component').then(c => c.ReturnViewComponent)
    }
];

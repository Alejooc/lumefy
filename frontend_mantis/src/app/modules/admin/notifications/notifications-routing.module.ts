import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';

const routes: Routes = [
    {
        path: 'templates',
        loadComponent: () => import('./templates/notification-templates.component').then(m => m.NotificationTemplatesComponent)
    },
    {
        path: 'send',
        loadComponent: () => import('./send/send-notification.component').then(m => m.SendNotificationComponent)
    }
];

@NgModule({
    imports: [RouterModule.forChild(routes)],
    exports: [RouterModule]
})
export class NotificationsRoutingModule { }

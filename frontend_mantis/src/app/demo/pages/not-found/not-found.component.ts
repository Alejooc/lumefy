import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
    selector: 'app-not-found',
    standalone: true,
    imports: [RouterModule],
    template: `
    <div class="not-found-container d-flex flex-column align-items-center justify-content-center">
      <h1 class="display-1 fw-bold text-primary">404</h1>
      <h4 class="mb-3">Página no encontrada</h4>
      <p class="text-muted mb-4">La página que buscas no existe o fue movida.</p>
      <a routerLink="/dashboard/default" class="btn btn-primary">
        <i class="feather icon-home me-2"></i>Ir al Dashboard
      </a>
    </div>
  `,
    styles: [`
    .not-found-container {
      min-height: 60vh;
      text-align: center;
    }
    .display-1 {
      font-size: 8rem;
      opacity: 0.3;
    }
  `]
})
export class NotFoundComponent { }

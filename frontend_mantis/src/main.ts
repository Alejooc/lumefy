import { enableProdMode, importProvidersFrom } from '@angular/core';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { environment } from './environments/environment';
import { BrowserModule, bootstrapApplication } from '@angular/platform-browser';
import { AppRoutingModule } from './app/app-routing.module';
import { provideAnimations } from '@angular/platform-browser/animations';
import { AppComponent } from './app/app.component';
import { JwtInterceptor } from './app/core/services/jwt.interceptor';
import { GlobalErrorInterceptor } from './app/core/interceptors/global-error.interceptor';

if (environment.production) {
  enableProdMode();
}

import { provideServiceWorker } from '@angular/service-worker';

bootstrapApplication(AppComponent, {
  providers: [
    importProvidersFrom(BrowserModule, AppRoutingModule),
    provideHttpClient(withInterceptorsFromDi()), // Enable interceptors
    provideAnimations(),
    provideServiceWorker('ngsw-worker.js', {
      enabled: environment.production,
      registrationStrategy: 'registerWhenStable:30000'
    }),
    { provide: HTTP_INTERCEPTORS, useClass: JwtInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: GlobalErrorInterceptor, multi: true }
  ]
}).catch((err) => console.error(err));

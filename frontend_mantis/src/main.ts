import { enableProdMode, importProvidersFrom, provideZoneChangeDetection } from '@angular/core';
import { HTTP_INTERCEPTORS, provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { environment } from './environments/environment';
import { BrowserModule, bootstrapApplication } from '@angular/platform-browser';
import { AppRoutingModule } from './app/app-routing.module';
import { provideAnimations } from '@angular/platform-browser/animations';
import { AppComponent } from './app/app.component';
import { JwtInterceptor } from './app/core/services/jwt.interceptor';
import { GlobalErrorInterceptor } from './app/core/interceptors/global-error.interceptor';
import { ZoneChangeDetectionInterceptor } from './app/core/interceptors/zone-change-detection.interceptor';

if (environment.production) {
  enableProdMode();
}


bootstrapApplication(AppComponent, {
  providers: [
    importProvidersFrom(BrowserModule, AppRoutingModule),
    provideZoneChangeDetection({ eventCoalescing: true, runCoalescing: true }),
    provideHttpClient(withInterceptorsFromDi()), // Enable interceptors
    provideAnimations(),
    { provide: HTTP_INTERCEPTORS, useClass: JwtInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: GlobalErrorInterceptor, multi: true },
    { provide: HTTP_INTERCEPTORS, useClass: ZoneChangeDetectionInterceptor, multi: true }
  ]
}).catch((err) => console.error(err));

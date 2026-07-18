import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable, NgZone, inject } from '@angular/core';
import { Observable } from 'rxjs';

/**
 * Keeps HTTP completion callbacks inside Angular's zone.
 *
 * Some legacy/browser integrations can deliver an HTTP observable callback outside
 * the zone. In that case component state changes correctly but the DOM is only
 * refreshed after the next user interaction. Wrapping the observer here makes the
 * update consistent for every module instead of requiring local detectChanges calls.
 */
@Injectable()
export class ZoneChangeDetectionInterceptor implements HttpInterceptor {
  private readonly zone = inject(NgZone);

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return new Observable<HttpEvent<unknown>>((subscriber) => {
      const subscription = next.handle(request).subscribe({
        next: (event) => this.zone.run(() => subscriber.next(event)),
        error: (error) => this.zone.run(() => subscriber.error(error)),
        complete: () => this.zone.run(() => subscriber.complete())
      });

      return () => subscription.unsubscribe();
    });
  }
}

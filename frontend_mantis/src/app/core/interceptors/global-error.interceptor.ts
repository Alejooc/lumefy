import { Injectable } from '@angular/core';
import {
    HttpRequest,
    HttpHandler,
    HttpEvent,
    HttpInterceptor,
    HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import Swal from 'sweetalert2';
import { Router } from '@angular/router';

@Injectable()
export class GlobalErrorInterceptor implements HttpInterceptor {

    constructor(private router: Router) { }

    intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        return next.handle(request).pipe(
            catchError((error: HttpErrorResponse) => {
                let errorMessage = '';
                let errorTitle = 'Error';
                let icon: 'error' | 'warning' | 'info' = 'error';

                if (error.error instanceof ErrorEvent) {
                    // Client-side error
                    errorMessage = `Error: ${error.error.message}`;
                } else {
                    // Server-side error
                    switch (error.status) {
                        case 401:
                            // Unauthorized - session expired or invalid token
                            if (!request.url.includes('/login')) {
                                icon = 'warning';
                                errorTitle = 'Sesión Expirada';
                                errorMessage = 'Tu sesión ha caducado. Por favor inicia sesión nuevamente.';
                                localStorage.removeItem('token');
                                this.router.navigate(['/login']);
                            }
                            break;
                        case 402:
                            icon = 'warning';
                            errorTitle = 'Límite de Plan';
                            errorMessage = error.error?.detail || 'Has alcanzado el límite de tu plan actual. Actualiza tu suscripción para continuar.';
                            break;
                        case 403:
                            icon = 'warning';
                            errorTitle = 'Acceso Denegado';
                            errorMessage = 'No tienes permisos para realizar esta acción.';
                            break;
                        case 404:
                            // Optional: Don't show alert for 404s if handled locally
                            errorTitle = 'No Encontrado';
                            errorMessage = 'El recurso solicitado no existe.';
                            break;
                        case 422:
                            errorTitle = 'Datos Inválidos';
                            errorMessage = this.formatValidationErrors(error.error);
                            icon = 'warning';
                            break;
                        case 500:
                            errorTitle = 'Error del Servidor';
                            errorMessage = 'Ocurrió un error interno en el servidor. Intenta nuevamente más tarde.';
                            break;
                        case 0:
                            errorTitle = 'Error de Conexión';
                            errorMessage = 'No se pudo conectar con el servidor. Verifica tu conexión a internet.';
                            break;
                        default:
                            errorTitle = `Error ${error.status}`;
                            errorMessage = error.error?.detail || error.message || 'Ocurrió un error inesperado.';
                    }
                }

                // Only show alert if we have a message and it's not a handled 401 login attempt
                if (errorMessage && !(error.status === 401 && request.url.includes('/login'))) {
                    Swal.fire({
                        title: errorTitle,
                        text: errorMessage,
                        icon: icon,
                        confirmButtonText: 'OK',
                        confirmButtonColor: '#0d6efd'
                    });
                }

                return throwError(() => error);
            })
        );
    }

    private formatValidationErrors(errorBody: any): string {
        if (errorBody && errorBody.detail && Array.isArray(errorBody.detail)) {
            return errorBody.detail.map((err: any) =>
                // Translate common Pydantic locations like ['body', 'email'] -> 'email'
                `${err.loc[err.loc.length - 1]}: ${err.msg}`
            ).join('\n');
        }
        return errorBody?.detail || 'Verifica los datos ingresados.';
    }
}

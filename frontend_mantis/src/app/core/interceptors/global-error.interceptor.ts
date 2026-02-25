import { Injectable, inject } from '@angular/core';
import { HttpErrorResponse, HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import Swal from 'sweetalert2';

interface ValidationErrorDetail {
    loc: Array<string | number>;
    msg: string;
    type: string;
    ctx?: { min_length?: number };
}

interface ValidationErrorBody {
    detail?: ValidationErrorDetail[] | string;
}

@Injectable()
export class GlobalErrorInterceptor implements HttpInterceptor {
    private router = inject(Router);

    intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
        return next.handle(request).pipe(
            catchError((error: HttpErrorResponse) => {
                let errorMessage = '';
                let errorTitle = 'Error';
                let icon: 'error' | 'warning' | 'info' = 'error';
                const errorPayload = error.error as ValidationErrorBody | undefined;

                if (error.error instanceof ErrorEvent) {
                    errorMessage = `Error: ${error.error.message}`;
                } else {
                    switch (error.status) {
                        case 401:
                            if (!request.url.includes('/login')) {
                                icon = 'warning';
                                errorTitle = 'Sesion expirada';
                                errorMessage = 'Tu sesion ha caducado. Por favor inicia sesion nuevamente.';
                                localStorage.removeItem('token');
                                this.router.navigate(['/login']);
                            }
                            break;
                        case 402:
                            icon = 'warning';
                            errorTitle = 'Limite de plan';
                            errorMessage =
                                typeof errorPayload?.detail === 'string'
                                    ? errorPayload.detail
                                    : 'Has alcanzado el limite de tu plan actual. Actualiza tu suscripcion para continuar.';
                            break;
                        case 403:
                            icon = 'warning';
                            errorTitle = 'Acceso denegado';
                            errorMessage = 'No tienes permisos para realizar esta accion.';
                            break;
                        case 404:
                            errorTitle = 'No encontrado';
                            errorMessage = 'El recurso solicitado no existe.';
                            break;
                        case 422:
                            errorTitle = 'Datos invalidos';
                            errorMessage = this.formatValidationErrors(errorPayload);
                            icon = 'warning';
                            break;
                        case 500:
                            errorTitle = 'Error del servidor';
                            errorMessage = 'Ocurrio un error interno en el servidor. Intenta nuevamente mas tarde.';
                            break;
                        case 0:
                            errorTitle = 'Error de conexion';
                            errorMessage = 'No se pudo conectar con el servidor. Verifica tu conexion a internet.';
                            break;
                        default:
                            errorTitle = `Error ${error.status}`;
                            errorMessage =
                                typeof errorPayload?.detail === 'string'
                                    ? errorPayload.detail
                                    : (error.message || 'Ocurrio un error inesperado.');
                    }
                }

                const suppressError = request.headers.get('X-Suppress-Error') === 'true';
                if (errorMessage && !(error.status === 401 && request.url.includes('/login')) && !suppressError) {
                    Swal.fire({
                        title: errorTitle,
                        text: errorMessage,
                        icon,
                        confirmButtonText: 'OK',
                        confirmButtonColor: '#0d6efd'
                    });
                }

                return throwError(() => error);
            })
        );
    }

    private formatValidationErrors(errorBody: ValidationErrorBody | undefined): string {
        if (Array.isArray(errorBody?.detail)) {
            return errorBody.detail
                .map((err: ValidationErrorDetail) => {
                    const field = String(err.loc[err.loc.length - 1]);
                    let msg = err.msg;

                    if (err.type === 'value_error.email') msg = 'El correo electronico no es valido.';
                    if (err.type === 'string_too_short') msg = `Debe tener al menos ${err.ctx?.min_length || 8} caracteres.`;
                    if (err.type === 'missing') msg = 'Este campo es requerido.';

                    return `- ${this.translateField(field)}: ${msg}`;
                })
                .join('\n');
        }

        if (typeof errorBody?.detail === 'string') {
            return errorBody.detail;
        }
        return 'Verifica los datos ingresados.';
    }

    private translateField(field: string): string {
        const map: Record<string, string> = {
            email: 'Correo',
            password: 'Contrasena',
            first_name: 'Nombre',
            last_name: 'Apellido',
            company_name: 'Nombre de empresa',
            phone: 'Telefono'
        };
        return map[field] || field;
    }
}

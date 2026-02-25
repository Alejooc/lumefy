import { Injectable } from '@angular/core';
import Swal from 'sweetalert2';
import { SweetAlertOptions, SweetAlertResult } from 'sweetalert2';

@Injectable({
    providedIn: 'root'
})
export class SweetAlertService {

    constructor() { }

    confirmDelete(): Promise<boolean> {
        return Swal.fire({
            title: '¿Estás seguro?',
            text: "¡No podrás revertir esto!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        }).then((result) => {
            return result.isConfirmed;
        });
    }

    confirm(title: string, text: string): Promise<SweetAlertResult> {
        return Swal.fire({
            title: title,
            text: text,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Sí, continuar',
            cancelButtonText: 'Cancelar'
        });
    }

    success(title: string, text: string = '') {
        Swal.fire({
            icon: 'success',
            title: title,
            text: text,
            timer: 1500,
            showConfirmButton: false
        });
    }

    error(title: string, text: string = '') {
        Swal.fire({
            icon: 'error',
            title: title,
            text: text
        });
    }
    warning(title: string, text: string = '') {
        Swal.fire({
            icon: 'warning',
            title: title,
            text: text
        });
    }

    toast(title: string, icon: 'success' | 'error' | 'warning' | 'info' = 'success') {
        Swal.fire({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 3000,
            timerProgressBar: true,
            icon: icon,
            title: title
        });
    }

    input(options: SweetAlertOptions): Promise<SweetAlertResult> {
        return Swal.fire(options);
    }

    close() {
        Swal.close();
    }
}

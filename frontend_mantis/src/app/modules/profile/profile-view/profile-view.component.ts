import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService, MfaEnableResult, MfaSetup, MfaStatus } from 'src/app/core/services/auth.service';
import { SharedModule } from 'src/app/theme/shared/shared.module';
import Swal from 'sweetalert2';
import { first } from 'rxjs/operators';

@Component({
    selector: 'app-profile-view',
    standalone: true,
    imports: [CommonModule, SharedModule, RouterModule, FormsModule],
    templateUrl: './profile-view.component.html',
    styleUrls: ['./profile-view.component.scss']
})
export class ProfileViewComponent implements OnInit {
    authService = inject(AuthService);
    user$ = this.authService.currentUser;
    mfaStatus: MfaStatus | null = null;
    mfaSetup: MfaSetup | null = null;
    recoveryCodes: string[] = [];
    mfaCode = '';
    mfaLoading = false;

    ngOnInit() {
        this.user$.pipe(first()).subscribe(user => {
            if (user?.is_superuser) {
                this.loadMfaStatus();
            }
        });
    }

    startMfaSetup() {
        this.mfaLoading = true;
        this.authService.setupMfa().subscribe({
            next: setup => {
                this.mfaSetup = setup;
                this.mfaLoading = false;
            },
            error: err => {
                this.mfaLoading = false;
                void Swal.fire('MFA', err.error?.detail || 'No se pudo iniciar la configuración.', 'error');
            }
        });
    }

    enableMfa() {
        if (!this.mfaCode.trim()) return;
        this.mfaLoading = true;
        this.authService.enableMfa(this.mfaCode.trim()).subscribe({
            next: (result: MfaEnableResult) => {
                this.mfaStatus = { enabled: true, configured: true, recovery_codes_remaining: result.recovery_codes.length };
                this.recoveryCodes = result.recovery_codes;
                this.mfaSetup = null;
                this.mfaCode = '';
                this.mfaLoading = false;
            },
            error: err => {
                this.mfaLoading = false;
                void Swal.fire('MFA', err.error?.detail || 'El código no es válido.', 'error');
            }
        });
    }

    disableMfa() {
        if (!this.mfaCode.trim()) return;
        this.mfaLoading = true;
        this.authService.disableMfa(this.mfaCode.trim()).subscribe({
            next: status => {
                this.mfaStatus = status;
                this.mfaCode = '';
                this.mfaLoading = false;
                void Swal.fire('MFA', 'MFA fue deshabilitado y las sesiones anteriores fueron revocadas.', 'success');
            },
            error: err => {
                this.mfaLoading = false;
                void Swal.fire('MFA', err.error?.detail || 'No se pudo deshabilitar MFA.', 'error');
            }
        });
    }

    revokeSessions() {
        this.mfaLoading = true;
        this.authService.revokeSessions().subscribe({
            next: () => {
                this.mfaLoading = false;
                void Swal.fire('Sesiones', 'Todas las sesiones fueron revocadas. Inicia sesión nuevamente.', 'success')
                    .then(() => this.authService.logout());
            },
            error: err => {
                this.mfaLoading = false;
                void Swal.fire('Sesiones', err.error?.detail || 'No se pudieron revocar las sesiones.', 'error');
            }
        });
    }

    private loadMfaStatus() {
        this.authService.getMfaStatus().subscribe({
            next: status => this.mfaStatus = status,
            error: () => this.mfaStatus = null
        });
    }
}

// project import
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';


@Component({
  selector: 'app-auth-login',
  standalone: true,
  imports: [RouterModule, ReactiveFormsModule],
  templateUrl: './auth-login.component.html',
  styleUrl: './auth-login.component.scss'
})
export class AuthLoginComponent {
  private fb = inject(FormBuilder);
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  loginForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]]
  });
  mfaForm = this.fb.group({
    code: ['', [Validators.required, Validators.minLength(6)]]
  });

  isLoading = false;
  errorMessage = '';
  mfaRequired = false;
  mfaChallengeToken = '';

  onSubmit() {
    if (this.mfaRequired) {
      this.onMfaSubmit();
      return;
    }
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    const { email, password } = this.loginForm.value;

    this.authService.login(email!, password!).subscribe({
      next: (result) => {
        if (result.mfaRequired && result.challengeToken) {
          this.mfaRequired = true;
          this.mfaChallengeToken = result.challengeToken;
          this.isLoading = false;
          return;
        }
        this.finishLogin(result.user);
      },
      error: (err) => {
        setTimeout(() => {
          this.isLoading = false;
          this.errorMessage = err?.status === 429
            ? 'Por seguridad, hemos limitado temporalmente los intentos de acceso. Espera un momento y vuelve a intentarlo.'
            : 'No fue posible iniciar sesión. Verifica tus credenciales.';
        });
      }
    });
  }

  onMfaSubmit() {
    if (this.mfaForm.invalid || !this.mfaChallengeToken) {
      this.mfaForm.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.authService.verifyMfa(this.mfaChallengeToken, this.mfaForm.value.code!).subscribe({
      next: (user) => this.finishLogin(user),
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err?.status === 429
          ? 'Demasiados intentos. Espera un momento antes de volver a intentarlo.'
          : 'El código MFA no es válido o ya fue utilizado.';
      }
    });
  }

  cancelMfa() {
    this.mfaRequired = false;
    this.mfaChallengeToken = '';
    this.mfaForm.reset();
    this.errorMessage = '';
  }

  private finishLogin(user: { is_superuser?: boolean } | null) {
    if (!user) {
      this.isLoading = false;
      return;
    }
    const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
    const defaultRoute = user.is_superuser ? '/admin/dashboard' : '/dashboard/default';
    void this.router.navigateByUrl(returnUrl || defaultRoute).finally(() => {
      this.isLoading = false;
    });
  }

}

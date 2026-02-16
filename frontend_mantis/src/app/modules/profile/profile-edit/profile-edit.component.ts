import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from 'src/app/core/services/auth.service';
import { ApiService } from 'src/app/core/services/api.service';
import Swal from 'sweetalert2';
import { first } from 'rxjs/operators';

import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { SharedModule } from 'src/app/theme/shared/shared.module';

@Component({
    selector: 'app-profile-edit',
    standalone: true,
    imports: [CommonModule, SharedModule, RouterModule, ReactiveFormsModule, FormsModule],
    templateUrl: './profile-edit.component.html'
})
export class ProfileEditComponent implements OnInit {
    form: FormGroup;
    loading = false;
    userId: string | null = null;

    private fb = inject(FormBuilder);
    private authService = inject(AuthService);
    private api = inject(ApiService);
    private router = inject(Router);

    constructor() {
        this.form = this.fb.group({
            full_name: ['', [Validators.required]],
            email: [{ value: '', disabled: true }], // Email usually not editable directly
            password: ['', [Validators.minLength(6)]], // Optional password change
            confirm_password: ['']
        });
    }

    ngOnInit() {
        this.authService.currentUser.pipe(first()).subscribe(user => {
            if (user) {
                this.userId = user.id;
                this.form.patchValue({
                    full_name: user.full_name,
                    email: user.email
                });
            }
        });
    }

    onSubmit() {
        if (this.form.invalid || !this.userId) return;

        const val = this.form.value;
        if (val.password && val.password !== val.confirm_password) {
            Swal.fire('Error', 'Las contraseñas no coinciden', 'error');
            return;
        }

        this.loading = true;
        const payload: any = {
            full_name: val.full_name
        };
        if (val.password) {
            payload.password = val.password;
        }

        // Usually users update their own profile via specific endpoint or generic update.
        // Assuming PUT /users/{id} works for self update if permissions allow, 
        // or we might need a specific /users/me endpoint. 
        // For MVP, if user has permission to edit users (admin), they can edit themselves.
        // If not, we might need to check permissions. 
        // Let's try PUT /users/{id}

        this.api.put(`/users/${this.userId}`, payload).subscribe({
            next: () => {
                Swal.fire('Éxito', 'Perfil actualizado correctamente', 'success');
                // Refresh auth user data
                this.authService.fetchMe().subscribe(() => {
                    this.loading = false;
                    this.router.navigate(['/profile/view']);
                });
            },
            error: (err) => {
                Swal.fire('Error', err.error?.detail || 'No se pudo actualizar el perfil', 'error');
                this.loading = false;
            }
        });
    }
}

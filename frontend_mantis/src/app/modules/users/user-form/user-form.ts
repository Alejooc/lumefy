import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { UserService } from '../user.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { Role } from '../user.model';

@Component({
  selector: 'app-user-form',
  templateUrl: './user-form.html',
  styleUrls: ['./user-form.scss'],
  standalone: false
})
export class UserFormComponent implements OnInit {
  userForm: FormGroup;
  isEditMode = false;
  userId: string | null = null;
  roles: Role[] = [];
  isLoading = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private userService: UserService,
    private swal: SweetAlertService
  ) {
    this.userForm = this.fb.group({
      full_name: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      password: [''], // Required only for creation
      role_id: [null, Validators.required],
      is_active: [true]
    });
  }

  ngOnInit(): void {
    this.loadRoles();
    this.userId = this.route.snapshot.paramMap.get('id');
    if (this.userId) {
      this.isEditMode = true;
      this.loadUser(this.userId);
    } else {
      this.userForm.get('password')?.setValidators([Validators.required, Validators.minLength(6)]);
    }
  }

  loadRoles() {
    this.userService.getRoles().subscribe(roles => {
      const priority: Record<string, number> = {
        ADMINISTRADOR: 1,
        GERENTE: 2,
        VENTAS_POS: 3,
        LOGISTICA: 4,
        INVENTARIO_COMPRAS: 5,
        REPORTES: 6
      };

      this.roles = [...roles].sort((a, b) => {
        const aKey = (a.name || '').toUpperCase();
        const bKey = (b.name || '').toUpperCase();
        const aPriority = priority[aKey] ?? 99;
        const bPriority = priority[bKey] ?? 99;
        if (aPriority !== bPriority) return aPriority - bPriority;
        return a.name.localeCompare(b.name);
      });
    });
  }

  get selectedRoleDescription(): string {
    const selectedRoleId = this.userForm.get('role_id')?.value;
    const selectedRole = this.roles.find(r => r.id === selectedRoleId);
    return selectedRole?.description || '';
  }

  loadUser(id: string) {
    this.isLoading = true;
    this.userService.getUser(id).subscribe({
      next: (user) => {
        this.userForm.patchValue({
          full_name: user.full_name,
          email: user.email,
          role_id: user.role_id,
          is_active: user.is_active
        });
        this.isLoading = false;
      },
      error: () => {
        this.swal.error('Error al cargar datos del usuario');
        this.router.navigate(['/users']);
      }
    });
  }

  onSubmit() {
    if (this.userForm.invalid) return;

    this.isLoading = true;
    const userData = this.userForm.value;

    if (this.isEditMode && !userData.password) {
      delete userData.password;
    }

    const request$ = this.isEditMode
      ? this.userService.updateUser(this.userId!, userData)
      : this.userService.createUser(userData);

    request$.subscribe({
      next: () => {
        this.swal.success(this.isEditMode ? 'Usuario actualizado' : 'Usuario creado');
        this.router.navigate(['/users']);
      },
      error: (err) => {
        console.error(err);
        this.swal.error(err.error?.detail || 'Error al guardar usuario');
        this.isLoading = false;
      }
    });
  }
}

import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { PermissionService } from '../../../core/services/permission.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { Role } from '../user.model';
import { UserService } from '../user.service';

type PermissionDef = {
  key: string;
  label: string;
  group: 'Empresa' | 'Usuarios' | 'Catalogo' | 'Inventario' | 'Ventas' | 'Reportes';
};

@Component({
  selector: 'app-role-management',
  templateUrl: './role-management.component.html',
  styleUrls: ['./role-management.component.scss'],
  standalone: false
})
export class RoleManagementComponent implements OnInit {
  private fb = inject(FormBuilder);
  private userService = inject(UserService);
  private swal = inject(SweetAlertService);
  private permissionService = inject(PermissionService);
  private router = inject(Router);

  roles: Role[] = [];
  loading = false;
  saving = false;
  isEditMode = false;
  editingRoleId: string | null = null;

  permissionDefs: PermissionDef[] = [
    { key: 'manage_company', label: 'Gestionar perfil de empresa', group: 'Empresa' },
    { key: 'manage_settings', label: 'Gestionar configuraciones operativas', group: 'Empresa' },
    { key: 'manage_users', label: 'Gestionar usuarios', group: 'Usuarios' },
    { key: 'view_dashboard', label: 'Ver dashboard', group: 'Reportes' },
    { key: 'view_products', label: 'Ver catalogo de productos', group: 'Catalogo' },
    { key: 'manage_inventory', label: 'Gestionar catalogo e inventario', group: 'Inventario' },
    { key: 'view_inventory', label: 'Ver inventario', group: 'Inventario' },
    { key: 'manage_clients', label: 'Gestionar clientes', group: 'Usuarios' },
    { key: 'create_sales', label: 'Crear ventas/cotizaciones', group: 'Ventas' },
    { key: 'view_sales', label: 'Ver ventas', group: 'Ventas' },
    { key: 'manage_sales', label: 'Gestionar estados de venta/logistica', group: 'Ventas' },
    { key: 'pos_access', label: 'Acceso a punto de venta (POS)', group: 'Ventas' },
    { key: 'view_reports', label: 'Ver reportes', group: 'Reportes' }
  ];

  roleForm: FormGroup;

  constructor() {
    this.roleForm = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(64)]],
      description: [''],
      permissions: this.fb.group(
        this.permissionDefs.reduce((acc, item) => {
          acc[item.key] = [false];
          return acc;
        }, {} as Record<string, boolean[]>)
      )
    });
  }

  ngOnInit(): void {
    if (!this.permissionService.hasPermission('manage_company')) {
      this.swal.error('No tienes permisos para gestionar roles.');
      this.router.navigate(['/dashboard/default']);
      return;
    }
    this.loadRoles();
  }

  get groupedPermissions(): { group: string; items: PermissionDef[] }[] {
    const groups: Record<string, PermissionDef[]> = {};
    for (const permission of this.permissionDefs) {
      if (!groups[permission.group]) groups[permission.group] = [];
      groups[permission.group].push(permission);
    }
    return Object.keys(groups).map((group) => ({ group, items: groups[group] }));
  }

  loadRoles(): void {
    this.loading = true;
    this.userService.getRoles().subscribe({
      next: (roles) => {
        this.roles = roles;
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error(err?.error?.detail || 'No se pudieron cargar los roles');
      }
    });
  }

  startCreate(): void {
    this.isEditMode = false;
    this.editingRoleId = null;
    this.roleForm.reset();
    this.clearPermissionChecks();
  }

  startEdit(role: Role): void {
    this.isEditMode = true;
    this.editingRoleId = role.id;
    this.roleForm.patchValue({
      name: role.name,
      description: role.description || ''
    });
    this.clearPermissionChecks();

    if (role.permissions?.['all']) {
      this.selectAllPermissions(true);
      return;
    }

    const permissionGroup = this.roleForm.get('permissions') as FormGroup;
    Object.keys(role.permissions || {}).forEach((key) => {
      if (permissionGroup.get(key)) {
        permissionGroup.get(key)?.setValue(!!role.permissions?.[key]);
      }
    });
  }

  toggleAllPermissions(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.selectAllPermissions(checked);
  }

  saveRole(): void {
    if (this.roleForm.invalid) {
      this.roleForm.markAllAsTouched();
      return;
    }

    const permissionsRaw = (this.roleForm.get('permissions') as FormGroup).value as Record<string, boolean>;
    const enabledPermissions = Object.entries(permissionsRaw).reduce((acc, [key, value]) => {
      if (value) acc[key] = true;
      return acc;
    }, {} as Record<string, boolean>);

    const payload: Partial<Role> = {
      name: this.roleForm.get('name')?.value,
      description: this.roleForm.get('description')?.value,
      permissions: enabledPermissions
    };

    this.saving = true;
    const request$ = this.isEditMode && this.editingRoleId
      ? this.userService.updateRole(this.editingRoleId, payload)
      : this.userService.createRole(payload);

    request$.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success(this.isEditMode ? 'Rol actualizado' : 'Rol creado');
        this.loadRoles();
        this.startCreate();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error(err?.error?.detail || 'No se pudo guardar el rol');
      }
    });
  }

  deleteRole(role: Role): void {
    if (role.permissions?.['all']) {
      this.swal.error('No puedes eliminar el rol administrador principal.');
      return;
    }

    this.swal.confirm('Eliminar rol', `Se eliminara el rol ${role.name}.`).then((result) => {
      if (!result.isConfirmed) return;
      this.userService.deleteRole(role.id).subscribe({
        next: () => {
          this.swal.success('Rol eliminado');
          this.loadRoles();
          if (this.editingRoleId === role.id) this.startCreate();
        },
        error: (err) => {
          this.swal.error(err?.error?.detail || 'No se pudo eliminar el rol');
        }
      });
    });
  }

  isAdminRole(role: Role): boolean {
    return !!role.permissions?.['all'];
  }

  private clearPermissionChecks(): void {
    this.selectAllPermissions(false);
  }

  private selectAllPermissions(value: boolean): void {
    const permissionGroup = this.roleForm.get('permissions') as FormGroup;
    Object.keys(permissionGroup.controls).forEach((key) => {
      permissionGroup.get(key)?.setValue(value);
    });
  }
}

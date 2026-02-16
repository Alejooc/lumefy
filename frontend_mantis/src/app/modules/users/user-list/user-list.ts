import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { UserService } from '../user.service';
import { User } from '../user.model';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';
import { PermissionService } from '../../../core/services/permission.service';

@Component({
  selector: 'app-user-list',
  templateUrl: './user-list.html',
  styleUrls: ['./user-list.scss'],
  standalone: false
})
export class UserListComponent implements OnInit {
  users: User[] = [];
  isLoading = false;
  canManageRoles = false;

  constructor(
    private userService: UserService,
    private swal: SweetAlertService,
    private permissionService: PermissionService,
    private cd: ChangeDetectorRef
  ) { }

  ngOnInit(): void {
    this.canManageRoles = this.permissionService.hasPermission('manage_company');
    this.loadUsers();
  }

  loadUsers() {
    this.isLoading = true;
    this.userService.getUsers().subscribe({
      next: (data) => {
        this.users = Array.isArray(data) ? data : [];
        this.isLoading = false;
        this.cd.detectChanges(); // Force update
      },
      error: (err) => {
        console.error('API Error:', err);
        this.isLoading = false;
        this.swal.error('Error al cargar usuarios');
      }
    });
  }

  deleteUser(id: string) {
    this.swal.confirm('¿Estás seguro?', 'El usuario no podrá acceder al sistema.').then((result) => {
      if (result.isConfirmed) {
        this.userService.deleteUser(id).subscribe({
          next: () => {
            this.swal.success('Usuario eliminado');
            this.loadUsers();
          },
          error: (err) => {
            console.error(err);
            this.swal.error('Error', 'No se pudo eliminar el usuario.');
          }
        });
      }
    });
  }
}

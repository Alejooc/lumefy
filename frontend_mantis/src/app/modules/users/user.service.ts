import { Injectable } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Observable } from 'rxjs';
import { User, Role } from './user.model';

@Injectable({
    providedIn: 'root'
})
export class UserService {

    constructor(private api: ApiService) { }

    getUsers(params: any = {}): Observable<User[]> {
        return this.api.get<User[]>('/users', params);
    }

    getUser(id: string): Observable<User> {
        return this.api.get<User>(`/users/${id}`);
    }

    createUser(user: Partial<User>): Observable<User> {
        return this.api.post<User>('/users', user);
    }

    updateUser(id: string, user: Partial<User>): Observable<User> {
        return this.api.put<User>(`/users/${id}`, user);
    }

    deleteUser(id: string): Observable<User> {
        return this.api.delete<User>(`/users/${id}`);
    }

    getRoles(): Observable<Role[]> {
        return this.api.get<Role[]>('/roles');
    }

    createRole(role: Partial<Role>): Observable<Role> {
        return this.api.post<Role>('/roles', role);
    }

    updateRole(id: string, role: Partial<Role>): Observable<Role> {
        return this.api.put<Role>(`/roles/${id}`, role);
    }

    deleteRole(id: string): Observable<Role> {
        return this.api.delete<Role>(`/roles/${id}`);
    }

    sendRecoveryEmail(id: string): Observable<any> {
        return this.api.post<any>(`/users/${id}/recovery-email`, {});
    }
}

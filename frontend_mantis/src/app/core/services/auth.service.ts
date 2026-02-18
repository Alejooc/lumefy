import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, catchError, tap, switchMap } from 'rxjs/operators';
import { ApiService } from './api.service';

export interface Role {
    id: string;
    name: string;
    permissions: { [key: string]: boolean };
}

export interface User {
    id: string;
    email: string;
    full_name: string;
    company_id: string;
    branch_id?: string;
    is_superuser?: boolean;
    is_active?: boolean;
    role?: Role;
    company?: Company;
}

export interface Company {
    id: string;
    name: string;
    currency: string;
    currency_symbol: string;
    plan?: string;
}

export interface Branch {
    id: string;
    name: string;
    is_warehouse: boolean;
    allow_pos: boolean;
    address?: string;
    phone?: string;
}

export interface UserRegister {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
    company_name: string;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private currentUserSubject: BehaviorSubject<User | null>;
    public currentUser: Observable<User | null>;

    private currentCompanySubject: BehaviorSubject<Company | null>;
    public currentCompany: Observable<Company | null>;

    constructor(
        private api: ApiService,
        private router: Router
    ) {
        this.currentUserSubject = new BehaviorSubject<User | null>(JSON.parse(localStorage.getItem('currentUser') || 'null'));
        this.currentUser = this.currentUserSubject.asObservable();

        this.currentCompanySubject = new BehaviorSubject<Company | null>(JSON.parse(localStorage.getItem('currentCompany') || 'null'));
        this.currentCompany = this.currentCompanySubject.asObservable();
    }

    public get currentUserValue(): User | null {
        return this.currentUserSubject.value;
    }

    public get currentCompanyValue(): Company | null {
        return this.currentCompanySubject.value;
    }

    login(username: string, password: string): Observable<any> {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        return this.api.post<any>('/login/access-token', formData).pipe(
            switchMap(response => {
                if (response && response.access_token) {
                    localStorage.setItem('access_token', response.access_token);
                    return this.fetchMe();
                }
                return of(null);
            })
        );
    }

    fetchMe(): Observable<any> {
        // First get user
        return this.api.get<User>('/users/me').pipe(
            tap(user => {
                localStorage.setItem('currentUser', JSON.stringify(user));
                this.currentUserSubject.next(user);

                // Then get company if user has one
                if (user.company_id) {
                    this.fetchCompany().subscribe();
                }
            })
        );
    }

    fetchCompany(): Observable<Company> {
        return this.api.get<Company>('/companies/me').pipe(
            tap(company => {
                localStorage.setItem('currentCompany', JSON.stringify(company));
                this.currentCompanySubject.next(company);
            })
        );
    }

    register(user: UserRegister): Observable<any> {
        return this.api.post<any>('/login/register', user).pipe(
            switchMap(response => {
                if (response && response.access_token) {
                    localStorage.setItem('access_token', response.access_token);
                    return this.fetchMe();
                }
                return of(null);
            })
        );
    }

    logout() {
        // remove user from local storage to log user out
        localStorage.removeItem('currentUser');
        localStorage.removeItem('currentCompany');
        localStorage.removeItem('access_token');
        this.currentUserSubject.next(null);
        this.currentCompanySubject.next(null);
        this.router.navigate(['/login']);
    }
}

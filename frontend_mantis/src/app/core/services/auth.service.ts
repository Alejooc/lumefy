import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, catchError, tap } from 'rxjs/operators';
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
    is_superuser?: boolean;
    role?: Role;
}

export interface Company {
    id: string;
    name: string;
    currency: string;
    currency_symbol: string;
}

export interface Branch {
    id: string;
    name: string;
    is_warehouse: boolean;
    allow_pos: boolean;
    address?: string;
    phone?: string;
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
            tap(response => {
                if (response && response.access_token) {
                    localStorage.setItem('access_token', response.access_token);
                    this.fetchMe().subscribe();
                }
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

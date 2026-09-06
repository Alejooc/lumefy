import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { map, switchMap, tap } from 'rxjs/operators';
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
    mfa_enabled?: boolean;
    role?: Role;
    company?: Company;
}

export interface Company {
    id: string;
    name: string;
    currency: string;
    currency_symbol: string;
    plan?: string;
    valid_until?: string | null;
    subscription_status?: string;
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

interface AuthTokenResponse {
    access_token?: string;
    mfa_required?: boolean;
    mfa_challenge?: string;
}

export interface LoginResult {
    user: User | null;
    mfaRequired: boolean;
    challengeToken?: string;
}

export interface MfaStatus {
    enabled: boolean;
    configured: boolean;
    recovery_codes_remaining: number;
}

export interface MfaSetup {
    enabled: boolean;
    secret: string;
    otpauth_uri: string;
}

export interface MfaEnableResult {
    enabled: boolean;
    recovery_codes: string[];
}

interface ImpersonationOrigin {
    access_token: string;
    user: User | null;
    company: Company | null;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    private readonly impersonationOriginKey = 'impersonation_origin';
    private api = inject(ApiService);
    private router = inject(Router);

    private currentUserSubject: BehaviorSubject<User | null>;
    public currentUser: Observable<User | null>;

    private currentCompanySubject: BehaviorSubject<Company | null>;
    public currentCompany: Observable<Company | null>;

    constructor() {
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

    get impersonationOriginUser(): User | null {
        return this.getImpersonationOrigin()?.user ?? null;
    }

    login(username: string, password: string): Observable<LoginResult> {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        return this.api.post<AuthTokenResponse>('/login/access-token', formData).pipe(
            switchMap(response => {
                if (response?.mfa_required && response.mfa_challenge) {
                    return of({
                        user: null,
                        mfaRequired: true,
                        challengeToken: response.mfa_challenge
                    });
                }
                if (response?.access_token) {
                    return this.completeLogin(response.access_token).pipe(
                        map(user => ({ user, mfaRequired: false }))
                    );
                }
                return of({ user: null, mfaRequired: false });
            })
        );
    }

    verifyMfa(challengeToken: string, code: string): Observable<User | null> {
        return this.api.post<AuthTokenResponse>('/login/mfa/verify', {
            challenge_token: challengeToken,
            code
        }).pipe(
            switchMap(response => response?.access_token ? this.completeLogin(response.access_token) : of(null))
        );
    }

    getMfaStatus(): Observable<MfaStatus> {
        return this.api.get<MfaStatus>('/login/mfa/status');
    }

    setupMfa(): Observable<MfaSetup> {
        return this.api.post<MfaSetup>('/login/mfa/setup', {});
    }

    enableMfa(code: string): Observable<MfaEnableResult> {
        return this.api.post<MfaEnableResult>('/login/mfa/enable', { code });
    }

    disableMfa(code: string): Observable<MfaStatus> {
        return this.api.post<MfaStatus>('/login/mfa/disable', { code });
    }

    revokeSessions(): Observable<{ msg: string }> {
        return this.api.post<{ msg: string }>('/login/sessions/revoke', {});
    }

    fetchMe(): Observable<User> {
        return this.api.get<User>('/users/me').pipe(
            switchMap(user => {
                if (!user.company_id) {
                    localStorage.removeItem('currentCompany');
                    this.currentCompanySubject.next(null);
                    return of(user);
                }

                return this.fetchCompany().pipe(map(() => user));
            }),
            tap(user => {
                localStorage.setItem('currentUser', JSON.stringify(user));
                this.currentUserSubject.next(user);
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

    register(user: UserRegister): Observable<User | null> {
        return this.api.post<AuthTokenResponse>('/register', user).pipe(
            switchMap(response => {
                if (response?.access_token) {
                    return this.completeLogin(response.access_token);
                }
                return of(null);
            })
        );
    }

    startImpersonation(accessToken: string): Observable<User> {
        if (!this.getImpersonationOrigin()) {
            const currentToken = localStorage.getItem('access_token');
            if (currentToken) {
                const origin: ImpersonationOrigin = {
                    access_token: currentToken,
                    user: this.currentUserValue,
                    company: this.currentCompanyValue
                };
                localStorage.setItem(this.impersonationOriginKey, JSON.stringify(origin));
            }
        }

        localStorage.setItem('access_token', accessToken);
        return this.fetchMe();
    }

    stopImpersonation(): Observable<User | null> {
        const origin = this.getImpersonationOrigin();
        if (!origin) {
            return of(null);
        }

        return this.api.post<{ ok: boolean }>('/admin/users/impersonation/end', {}).pipe(
            switchMap(() => {
                localStorage.setItem('access_token', origin.access_token);
                return this.fetchMe();
            }),
            tap(() => this.clearImpersonationOrigin())
        );
    }

    isImpersonating(): boolean {
        return this.getImpersonationOrigin() !== null;
    }

    logout(): void {
        localStorage.removeItem('currentUser');
        localStorage.removeItem('currentCompany');
        localStorage.removeItem('access_token');
        this.clearImpersonationOrigin();
        this.currentUserSubject.next(null);
        this.currentCompanySubject.next(null);
        this.router.navigate(['/login']);
    }

    private getImpersonationOrigin(): ImpersonationOrigin | null {
        try {
            const stored = localStorage.getItem(this.impersonationOriginKey);
            return stored ? JSON.parse(stored) as ImpersonationOrigin : null;
        } catch {
            this.clearImpersonationOrigin();
            return null;
        }
    }

    private completeLogin(accessToken: string): Observable<User> {
        this.clearImpersonationOrigin();
        localStorage.setItem('access_token', accessToken);
        return this.fetchMe();
    }

    private clearImpersonationOrigin(): void {
        localStorage.removeItem(this.impersonationOriginKey);
    }
}

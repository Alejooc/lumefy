import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, timer, switchMap, retry, share, tap, catchError, of } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Notification {
    id: string;
    type: 'info' | 'success' | 'warning' | 'danger';
    title: string;
    message: string;
    link?: string;
    is_read: boolean;
    created_at: string;
}

@Injectable({
    providedIn: 'root'
})
export class NotificationService {
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiUrl}/notifications`;

    private unreadCountSubject = new BehaviorSubject<number>(0);
    unreadCount$ = this.unreadCountSubject.asObservable();

    // Polling observable
    // Poll every 60 seconds
    notifications$ = timer(0, 60000).pipe(
        switchMap(() => this.getUnread()),
        retry(3),
        share()
    );

    constructor() {
        // Initial fetch
        this.refresh();
    }

    refresh() {
        this.getUnread().subscribe();
    }

    getUnread(): Observable<Notification[]> {
        return this.http.get<Notification[]>(`${this.apiUrl}/unread`).pipe(
            tap(notifications => {
                this.unreadCountSubject.next(notifications.length);
            }),
            catchError(() => {
                return of([]);
            })
        );
    }

    getAll(skip = 0, limit = 50): Observable<Notification[]> {
        return this.http.get<Notification[]>(`${this.apiUrl}?skip=${skip}&limit=${limit}`);
    }

    markAsRead(id: string): Observable<Notification> {
        return this.http.put<Notification>(`${this.apiUrl}/${id}/read`, {}).pipe(
            tap(() => {
                // Decrease count locally for instant feedback
                const current = this.unreadCountSubject.value;
                if (current > 0) this.unreadCountSubject.next(current - 1);
            })
        );
    }

    markAllAsRead(): Observable<any> {
        return this.http.put(`${this.apiUrl}/read-all`, {}).pipe(
            tap(() => {
                this.unreadCountSubject.next(0);
            })
        );
    }
}

import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditService, AuditLog } from '../../../core/services/audit.service';
import { ApiService } from '../../../core/services/api.service';

@Component({
    selector: 'app-audit-list',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './audit-list.component.html',
    styleUrls: ['./audit-list.component.scss']
})
export class AuditListComponent implements OnInit {
    private auditService = inject(AuditService);
    private apiService = inject(ApiService);
    private cdr = inject(ChangeDetectorRef);

    logs: AuditLog[] = [];
    isLoading = false;

    // Filters
    filterAction = '';
    filterEntityType = '';
    filterUserId = '';
    dateFrom = '';
    dateTo = '';

    // Users for dropdown
    users: any[] = [];

    // Known action types
    actionTypes = ['CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'EXPORT', 'STATUS_CHANGE'];

    // Known entity types
    entityTypes = ['Product', 'Sale', 'Client', 'PurchaseOrder', 'Inventory', 'User', 'Branch', 'Company'];

    ngOnInit() {
        this.loadUsers();
        this.loadLogs();
    }

    loadUsers() {
        this.apiService.get<any[]>('/users').subscribe({
            next: (data) => {
                this.users = data;
                this.cdr.detectChanges();
            },
            error: () => { }
        });
    }

    loadLogs() {
        this.isLoading = true;
        const filters: any = {};
        if (this.filterAction) filters.action = this.filterAction;
        if (this.filterEntityType) filters.entity_type = this.filterEntityType;
        if (this.filterUserId) filters.user_id = this.filterUserId;
        if (this.dateFrom) filters.date_from = this.dateFrom;
        if (this.dateTo) filters.date_to = this.dateTo;

        this.auditService.getAuditLogs(1, 100, filters).subscribe({
            next: (logs) => {
                this.logs = logs;
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }

    applyFilters() {
        this.loadLogs();
    }

    clearFilters() {
        this.filterAction = '';
        this.filterEntityType = '';
        this.filterUserId = '';
        this.dateFrom = '';
        this.dateTo = '';
        this.loadLogs();
    }

    get hasActiveFilters(): boolean {
        return !!(this.filterAction || this.filterEntityType || this.filterUserId || this.dateFrom || this.dateTo);
    }

    getBadgeClass(action: string): string {
        switch (action) {
            case 'CREATE': return 'bg-success';
            case 'UPDATE': return 'bg-warning text-dark';
            case 'DELETE': return 'bg-danger';
            case 'LOGIN': return 'bg-info';
            case 'LOGOUT': return 'bg-secondary';
            case 'STATUS_CHANGE': return 'bg-primary';
            default: return 'bg-secondary';
        }
    }
}

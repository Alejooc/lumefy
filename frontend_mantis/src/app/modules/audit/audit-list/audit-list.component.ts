import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditService, AuditLog } from '../../../core/services/audit.service';

@Component({
    selector: 'app-audit-list',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './audit-list.component.html',
    styleUrls: ['./audit-list.component.scss']
})
export class AuditListComponent implements OnInit {
    private auditService = inject(AuditService);
    logs: AuditLog[] = [];

    ngOnInit() {
        this.auditService.getAuditLogs().subscribe(logs => {
            this.logs = logs;
        });
    }

    getBadgeClass(action: string): string {
        switch (action) {
            case 'CREATE': return 'bg-success';
            case 'UPDATE': return 'bg-warning text-dark';
            case 'DELETE': return 'bg-danger';
            case 'LOGIN': return 'bg-info';
            default: return 'bg-secondary';
        }
    }
}

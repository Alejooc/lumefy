import { Directive, Input, TemplateRef, ViewContainerRef, OnInit, OnDestroy } from '@angular/core';
import { PermissionService } from '../../../core/services/permission.service';
import { AuthService } from '../../../core/services/auth.service';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';

@Directive({
    selector: '[appHasPermission]',
    standalone: true
})
export class HasPermissionDirective implements OnInit, OnDestroy {
    private permission: string = '';
    private destroy$ = new Subject<void>();

    constructor(
        private templateRef: TemplateRef<any>,
        private viewContainer: ViewContainerRef,
        private permissionService: PermissionService,
        private authService: AuthService
    ) { }

    @Input()
    set appHasPermission(val: string) {
        this.permission = val;
        this.updateView();
    }

    ngOnInit() {
        this.authService.currentUser.pipe(takeUntil(this.destroy$)).subscribe(() => {
            this.updateView();
        });
    }

    ngOnDestroy() {
        this.destroy$.next();
        this.destroy$.complete();
    }

    private updateView() {
        this.viewContainer.clear();
        if (this.permissionService.hasPermission(this.permission)) {
            this.viewContainer.createEmbeddedView(this.templateRef);
        }
    }
}

import { Component, OnInit, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { AdminService, SystemSetting } from '../admin.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-admin-settings',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule, SharedModule],
    templateUrl: './admin-settings.component.html'
})
export class AdminSettingsComponent implements OnInit {
    settingsForm: FormGroup;
    loading = false;
    settings: SystemSetting[] = [];

    private fb = inject(FormBuilder);
    private adminService = inject(AdminService);
    private cdr = inject(ChangeDetectorRef);

    constructor() {
        this.settingsForm = this.fb.group({
            // Branding
            system_name: ['Lumefy SaaS'],
            logo_url: [''],
            primary_color: ['#4680ff'],

            // Defaults
            default_currency: ['USD'],
            default_language: ['es'],

            // System
            maintenance_mode: [false],
            allow_registrations: [true]
        });
    }

    ngOnInit() {
        this.loadSettings();
    }

    loadSettings() {
        this.loading = true;
        this.adminService.getSettings().subscribe({
            next: (data) => {
                this.settings = data;

                // Map array to form
                const formVal: any = {};
                data.forEach(s => {
                    if (this.settingsForm.contains(s.key)) {
                        // Convert boolean strings if needed
                        let val: any = s.value;
                        if (s.value === 'true') val = true;
                        if (s.value === 'false') val = false;
                        formVal[s.key] = val;
                    }
                });

                this.settingsForm.patchValue(formVal);
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error(err);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    onSubmit() {
        this.loading = true;
        const formVal = this.settingsForm.value;
        const updates: any[] = [];

        Object.keys(formVal).forEach(key => {
            let val = formVal[key];
            if (val === true) val = 'true';
            if (val === false) val = 'false';

            updates.push({
                key: key,
                value: String(val),
                group: this.getGroup(key),
                is_public: this.isPublic(key)
            });
        });

        this.adminService.updateSettings(updates).subscribe({
            next: () => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Guardado', 'Configuración actualizada', 'success');
            },
            error: (err) => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo guardar la configuración', 'error');
            }
        });
    }

    getGroup(key: string): string {
        if (['system_name', 'logo_url', 'primary_color'].includes(key)) return 'branding';
        if (['default_currency', 'default_language'].includes(key)) return 'defaults';
        return 'system';
    }

    isPublic(key: string): boolean {
        return ['system_name', 'logo_url', 'primary_color', 'maintenance_mode'].includes(key);
    }
}

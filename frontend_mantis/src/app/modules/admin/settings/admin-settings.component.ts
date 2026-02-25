import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, ReactiveFormsModule } from '@angular/forms';
import Swal from 'sweetalert2';
import { SharedModule } from '../../../theme/shared/shared.module';
import { AdminService, SystemSetting } from '../admin.service';

type SettingsUpdate = Pick<SystemSetting, 'key' | 'value' | 'group' | 'is_public'>;

@Component({
    selector: 'app-admin-settings',
    standalone: true,
    imports: [ReactiveFormsModule, SharedModule],
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
            system_name: ['Lumefy SaaS'],
            logo_url: [''],
            primary_color: ['#4680ff'],
            default_currency: ['USD'],
            default_language: ['es'],
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
                const formVal: Record<string, string | boolean> = {};
                data.forEach((setting) => {
                    if (this.settingsForm.contains(setting.key)) {
                        let value: string | boolean = setting.value;
                        if (setting.value === 'true') value = true;
                        if (setting.value === 'false') value = false;
                        formVal[setting.key] = value;
                    }
                });

                this.settingsForm.patchValue(formVal);
                this.loading = false;
                this.cdr.detectChanges();
            },
            error: (error: unknown) => {
                console.error(error);
                this.loading = false;
                this.cdr.detectChanges();
            }
        });
    }

    onSubmit() {
        this.loading = true;
        const formVal = this.settingsForm.value as Record<string, unknown>;
        const updates: SettingsUpdate[] = [];

        Object.keys(formVal).forEach((key) => {
            let value = formVal[key];
            if (value === true) value = 'true';
            if (value === false) value = 'false';

            updates.push({
                key,
                value: String(value ?? ''),
                group: this.getGroup(key),
                is_public: this.isPublic(key)
            });
        });

        this.adminService.updateSettings(updates).subscribe({
            next: () => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Guardado', 'Configuracion actualizada', 'success');
            },
            error: () => {
                this.loading = false;
                this.cdr.detectChanges();
                Swal.fire('Error', 'No se pudo guardar la configuracion', 'error');
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

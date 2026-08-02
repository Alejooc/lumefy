import { CommonModule } from '@angular/common';
import { Component, OnInit, TemplateRef, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import {
  Storefront,
  StorefrontAdminService,
  StorefrontShippingConfig,
  StorefrontShippingDestination,
  StorefrontShippingDestinationImportResult,
  StorefrontShippingMethod,
  StorefrontShippingRule
} from 'src/app/core/services/storefront-admin.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

type LogisticsSection = 'destinations' | 'methods' | 'rules';

type DestinationForm = {
  country_code: string;
  state_code: string;
  state_name: string;
  city_code: string;
  city_name: string;
  destination_type: string;
  sort_order: number;
};

type MethodForm = {
  code: string;
  name: string;
  description: string;
  method_type: string;
  is_enabled: boolean;
  sort_order: number;
  estimate_min_days: number | null;
  estimate_max_days: number | null;
};

type RuleForm = {
  method_id: string;
  name: string;
  priority: number;
  is_enabled: boolean;
  destination_type: string;
  country_code: string;
  state_code: string;
  state_name: string;
  city_code: string;
  city_name: string;
  payment_provider: string;
  min_subtotal: number | null;
  max_subtotal: number | null;
  min_weight: number | null;
  max_weight: number | null;
  charge_type: string;
  amount: number;
  rate_per_kg: number;
  estimate_min_days: number | null;
  estimate_max_days: number | null;
};

@Component({
  selector: 'app-ecommerce-logistics',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-logistics.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-logistics.component.scss']
})
export class EcommerceLogisticsComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);
  private modalService = inject(NgbModal);

  loading = false;
  saving = false;
  section: LogisticsSection = 'destinations';
  storefronts: Storefront[] = [];
  storefront: Storefront | null = null;
  selectedStorefrontId = '';
  destinations: StorefrontShippingDestination[] = [];
  methods: StorefrontShippingMethod[] = [];
  rules: StorefrontShippingRule[] = [];
  importFile: File | null = null;
  importing = false;
  importResult: StorefrontShippingDestinationImportResult | null = null;
  editingDestinationId: string | null = null;
  editingMethodId: string | null = null;
  editingRuleId: string | null = null;

  destinationForm = this.createDestinationForm();
  methodForm = this.createMethodForm();
  ruleForm = this.createRuleForm();

  readonly destinationTypes = [
    { value: 'department', label: 'Departamento completo' },
    { value: 'city', label: 'Ciudad específica' }
  ];
  readonly methodTypes = [
    { value: 'delivery', label: 'Entrega a domicilio' },
    { value: 'pickup', label: 'Recogida en tienda' },
    { value: 'quote', label: 'Cotización manual' }
  ];
  readonly chargeTypes = [
    { value: 'flat', label: 'Tarifa fija' },
    { value: 'free', label: 'Envío gratis' },
    { value: 'weight', label: 'Base + valor por kg' },
    { value: 'percentage', label: 'Porcentaje del subtotal' },
    { value: 'quote', label: 'Cotizar después' }
  ];

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar la logística de ecommerce.');
      return;
    }
    this.loadStorefronts();
  }

  loadStorefronts(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.applySelectedStorefront();
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudieron cargar las tiendas.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.applySelectedStorefront();
  }

  loadConfig(): void {
    if (!this.selectedStorefrontId) {
      return;
    }
    this.loading = true;
    this.storefrontService.getShippingConfig(this.selectedStorefrontId).subscribe({
      next: (config) => {
        this.applyConfig(config);
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la configuración logística.');
      }
    });
  }

  saveDestination(): void {
    if (!this.storefront || !this.destinationForm.state_name.trim()) {
      return;
    }
    this.saving = true;
    const payload = { storefront_id: this.storefront.id, ...this.destinationForm };
    const request = this.editingDestinationId
      ? this.storefrontService.updateShippingDestination(this.editingDestinationId, payload)
      : this.storefrontService.createShippingDestination(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success(this.editingDestinationId ? 'Destino actualizado' : 'Destino creado');
        this.modalService.dismissAll();
        this.resetDestination();
        this.loadConfig();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('No se pudo guardar', err?.error?.detail || 'Revisa los datos del destino.');
      }
    });
  }

  openImportModal(content: TemplateRef<unknown>): void {
    this.importFile = null;
    this.importResult = null;
    this.modalService.open(content, { centered: true, size: 'lg', scrollable: true });
  }

  onImportFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.importFile = input.files?.[0] || null;
    this.importResult = null;
  }

  importDestinations(): void {
    if (!this.storefront || !this.importFile) {
      return;
    }
    this.importing = true;
    this.storefrontService.importShippingDestinations(this.storefront.id, this.importFile).subscribe({
      next: (result) => {
        this.importing = false;
        this.importResult = result;
        this.loadConfig();
        if (result.error_count) {
          this.swal.error('Importación parcial', `Se procesaron ${result.count} destinos y quedaron ${result.error_count} filas con errores.`);
        } else {
          this.swal.success('Importación completada', `Se procesaron ${result.count} destinos correctamente.`);
        }
      },
      error: (err) => {
        this.importing = false;
        this.swal.error('No se pudo importar', err?.error?.detail || 'Revisa el formato y las columnas del archivo.');
      }
    });
  }

  downloadImportTemplate(): void {
    const content = [
      'country_code,state_code,state_name,city_code,city_name,destination_type,sort_order',
      'CO,76,Valle del Cauca,76001,Cali,city,0',
      'CO,76,Valle del Cauca,,,department,0'
    ].join('\n');
    const blob = new Blob([`\ufeff${content}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'plantilla-destinos-logistica.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  }

  saveMethod(): void {
    if (!this.storefront || !this.methodForm.code.trim() || !this.methodForm.name.trim()) {
      return;
    }
    this.saving = true;
    const payload = { storefront_id: this.storefront.id, ...this.methodForm };
    const request = this.editingMethodId
      ? this.storefrontService.updateShippingMethod(this.editingMethodId, payload)
      : this.storefrontService.createShippingMethod(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success(this.editingMethodId ? 'Método actualizado' : 'Método creado');
        this.modalService.dismissAll();
        this.resetMethod();
        this.loadConfig();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('No se pudo guardar', err?.error?.detail || 'Revisa los datos del método.');
      }
    });
  }

  saveRule(): void {
    if (!this.storefront || !this.ruleForm.method_id || !this.ruleForm.name.trim()) {
      return;
    }
    this.saving = true;
    const payload = {
      storefront_id: this.storefront.id,
      ...this.ruleForm,
      payment_provider: this.ruleForm.payment_provider || null,
      country_code: this.ruleForm.country_code || null,
      state_code: this.ruleForm.state_code || null,
      state_name: this.ruleForm.state_name || null,
      city_code: this.ruleForm.city_code || null,
      city_name: this.ruleForm.city_name || null
    };
    const request = this.editingRuleId
      ? this.storefrontService.updateShippingRule(this.editingRuleId, payload)
      : this.storefrontService.createShippingRule(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.swal.success(this.editingRuleId ? 'Regla actualizada' : 'Regla creada');
        this.modalService.dismissAll();
        this.resetRule();
        this.loadConfig();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('No se pudo guardar', err?.error?.detail || 'Revisa las condiciones de la regla.');
      }
    });
  }

  openDestinationModal(content: TemplateRef<unknown>, item?: StorefrontShippingDestination): void {
    this.section = 'destinations';
    this.editingDestinationId = item?.id || null;
    this.destinationForm = item
      ? {
          country_code: item.country_code || 'CO',
          state_code: item.state_code || '',
          state_name: item.state_name,
          city_code: item.city_code || '',
          city_name: item.city_name || '',
          destination_type: item.destination_type,
          sort_order: item.sort_order
        }
      : this.createDestinationForm();
    this.modalService.open(content, { centered: true, size: 'lg', scrollable: true });
  }

  openMethodModal(content: TemplateRef<unknown>, item?: StorefrontShippingMethod): void {
    this.section = 'methods';
    this.editingMethodId = item?.id || null;
    this.methodForm = item
      ? {
          code: item.code,
          name: item.name,
          description: item.description || '',
          method_type: item.method_type,
          is_enabled: item.is_enabled,
          sort_order: item.sort_order,
          estimate_min_days: item.estimate_min_days ?? null,
          estimate_max_days: item.estimate_max_days ?? null
        }
      : this.createMethodForm();
    this.modalService.open(content, { centered: true, size: 'lg', scrollable: true });
  }

  openRuleModal(content: TemplateRef<unknown>, item?: StorefrontShippingRule): void {
    this.section = 'rules';
    this.editingRuleId = item?.id || null;
    this.ruleForm = item
      ? {
          method_id: item.method_id,
          name: item.name,
          priority: item.priority,
          is_enabled: item.is_enabled,
          destination_type: item.destination_type,
          country_code: item.country_code || 'CO',
          state_code: item.state_code || '',
          state_name: item.state_name || '',
          city_code: item.city_code || '',
          city_name: item.city_name || '',
          payment_provider: item.payment_provider || '',
          min_subtotal: item.min_subtotal ?? null,
          max_subtotal: item.max_subtotal ?? null,
          min_weight: item.min_weight ?? null,
          max_weight: item.max_weight ?? null,
          charge_type: item.charge_type,
          amount: item.amount,
          rate_per_kg: item.rate_per_kg,
          estimate_min_days: item.estimate_min_days ?? null,
          estimate_max_days: item.estimate_max_days ?? null
        }
      : this.createRuleForm();
    if (!item && this.methods.length) this.ruleForm.method_id = this.methods[0].id;
    this.modalService.open(content, { centered: true, size: 'xl', scrollable: true });
  }

  async remove(kind: LogisticsSection, id: string): Promise<void> {
    const confirmation = await this.swal.confirm('Desactivar configuración', 'No se usará en nuevos pedidos. Las órdenes existentes no cambian.');
    if (!confirmation.isConfirmed) {
      return;
    }
    const request = kind === 'destinations'
      ? this.storefrontService.deleteShippingDestination(id)
      : kind === 'methods'
        ? this.storefrontService.deleteShippingMethod(id)
        : this.storefrontService.deleteShippingRule(id);
    request.subscribe({
      next: () => {
        this.swal.success('Configuración desactivada');
        this.loadConfig();
      },
      error: (err) => this.swal.error('No se pudo desactivar', err?.error?.detail || 'Intenta de nuevo.')
    });
  }

  methodName(methodId: string): string {
    return this.methods.find((method) => method.id === methodId)?.name || 'Método eliminado';
  }

  destinationLabel(item: StorefrontShippingDestination): string {
    return item.city_name ? `${item.city_name}, ${item.state_name}` : item.state_name;
  }

  ruleChargeLabel(item: StorefrontShippingRule): string {
    if (item.charge_type === 'free') return 'Gratis';
    if (item.charge_type === 'quote') return 'Cotizar';
    if (item.charge_type === 'weight') return `Base ${item.amount} + ${item.rate_per_kg}/kg`;
    if (item.charge_type === 'percentage') return `${item.amount}% del subtotal`;
    return `${item.amount}`;
  }

  private applySelectedStorefront(): void {
    this.storefront = this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
    this.resetDestination();
    this.resetMethod();
    this.resetRule();
    this.loadConfig();
  }

  private applyConfig(config: StorefrontShippingConfig): void {
    this.destinations = config.destinations || [];
    this.methods = config.methods || [];
    this.rules = config.rules || [];
    if (!this.ruleForm.method_id && this.methods.length) {
      this.ruleForm.method_id = this.methods[0].id;
    }
  }

  resetDestination(): void {
    this.editingDestinationId = null;
    this.destinationForm = this.createDestinationForm();
  }

  resetMethod(): void {
    this.editingMethodId = null;
    this.methodForm = this.createMethodForm();
  }

  resetRule(): void {
    this.editingRuleId = null;
    this.ruleForm = this.createRuleForm();
    if (this.methods.length) this.ruleForm.method_id = this.methods[0].id;
  }

  private createDestinationForm(): DestinationForm {
    return { country_code: 'CO', state_code: '', state_name: '', city_code: '', city_name: '', destination_type: 'city', sort_order: 0 };
  }

  private createMethodForm(): MethodForm {
    return { code: '', name: '', description: '', method_type: 'delivery', is_enabled: true, sort_order: 0, estimate_min_days: null, estimate_max_days: null };
  }

  private createRuleForm(): RuleForm {
    return { method_id: '', name: '', priority: 100, is_enabled: true, destination_type: 'global', country_code: 'CO', state_code: '', state_name: '', city_code: '', city_name: '', payment_provider: '', min_subtotal: null, max_subtotal: null, min_weight: null, max_weight: null, charge_type: 'flat', amount: 0, rate_per_kg: 0, estimate_min_days: null, estimate_max_days: null };
  }
}

import { Component, OnInit, inject } from '@angular/core';

import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule, Validators, FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { PriceList, PriceListItem, PriceListService, PriceListSourceRule, PriceListSourceRulePayload } from '../../../core/services/pricelist.service';
import { ProductService, Product } from '../../../core/services/product.service';
import { IntegrationService, IntegrationSource } from '../../../core/services/integration.service';
import Swal from 'sweetalert2';

@Component({
    selector: 'app-pricelist-form',
    standalone: true,
    imports: [ReactiveFormsModule, FormsModule, RouterModule],
    templateUrl: './pricelist-form.component.html',
    styleUrls: ['./pricelist-form.component.scss']
})
export class PriceListFormComponent implements OnInit {
    priceListForm: FormGroup;
    products: Product[] = [];
    isEditMode = false;
    priceListId: string | null = null;
    loading = false;
    error = '';
    sources: IntegrationSource[] = [];
    globalPercent = 0;
    globalBaseSource: PriceList['base_source'] = 'EXTERNAL_PRICE';
    preserveOverrides = false;
    selectedFile: File | null = null;
    importing = false;
    importResult: { rows_received: number; rows_failed: number; errors: string[] } | null = null;
    private removedItemIds = new Set<string>();
    sourceRules: PriceListSourceRule[] = [];
    private removedSourceRuleIds = new Set<string>();

    private fb = inject(FormBuilder);
    private router = inject(Router);
    private route = inject(ActivatedRoute);
    private priceListService = inject(PriceListService);
    private productService = inject(ProductService);
    private integrationService = inject(IntegrationService);

    constructor() {
        this.priceListForm = this.fb.group({
            name: ['', Validators.required],
            type: ['SALE', Validators.required],
            currency: ['USD', Validators.required],
            active: [true],
            source_id: [null],
            pricing_mode: ['FIXED', Validators.required],
            base_source: ['INTERNAL_PRICE', Validators.required],
            adjustment_value: [0, [Validators.required, Validators.min(-1000000)]],
            rounding_step: [0, [Validators.min(0)]],
            min_margin_percent: [null, [Validators.min(0)]],
            items: this.fb.array([])
        });
    }

    get items() {
        return this.priceListForm.get('items') as FormArray;
    }

    ngOnInit() {
        this.loadProducts();
        this.integrationService.listSources().subscribe({ next: (sources) => this.sources = sources.filter((source) => source.is_active) });
        this.route.paramMap.subscribe(params => {
            this.priceListId = params.get('id');
            if (this.priceListId) {
                this.isEditMode = true;
                this.loadPriceList(this.priceListId);
            }
        });
    }

    loadProducts() {
        this.productService.getProductsForPriceList().subscribe(data => this.products = data);
    }

    loadPriceList(id: string) {
        this.priceListService.getPriceList(id).subscribe(pl => {
            this.priceListForm.patchValue({
                name: pl.name,
                type: pl.type,
                currency: pl.currency,
                active: pl.active,
                source_id: pl.source_id || null,
                pricing_mode: pl.pricing_mode || 'FIXED',
                base_source: pl.base_source || 'INTERNAL_PRICE',
                adjustment_value: pl.adjustment_value || 0,
                rounding_step: pl.rounding_step || 0,
                min_margin_percent: pl.min_margin_percent ?? null
            });

            // Load items
            this.items.clear();
            this.removedItemIds.clear();
            pl.items?.forEach(item => {
                this.items.push(this.createItemGroup(item));
            });
            this.sourceRules = (pl.source_rules || []).map(rule => ({ ...rule }));
            this.removedSourceRuleIds.clear();
        });
    }

    createItemGroup(item?: PriceListItem): FormGroup {
        return this.fb.group({
            id: [item?.id || null],
            product_id: [item?.product_id || '', Validators.required],
            variant_id: [item?.variant_id || null],
            min_quantity: [item?.min_quantity || 0, [Validators.required, Validators.min(0)]],
            price: [item?.price ?? null, [Validators.min(0)]]
        });
    }

    addItem() {
        this.items.push(this.createItemGroup());
    }

    removeItem(index: number) {
        const id = this.items.at(index).get('id')?.value as string | null;
        if (id) this.removedItemIds.add(id);
        this.items.removeAt(index);
    }

    addSourceRule(): void {
        this.sourceRules.push({
            source_id: '',
            pricing_mode: 'MARKUP_PERCENT',
            base_source: 'EXTERNAL_PRICE',
            adjustment_value: 0,
            rounding_step: 0,
            min_margin_percent: null
        });
    }

    removeSourceRule(index: number): void {
        const rule = this.sourceRules[index];
        if (rule?.id) this.removedSourceRuleIds.add(rule.id);
        this.sourceRules.splice(index, 1);
    }

    private validateSourceRules(): string | null {
        if (this.priceListForm.get('type')?.value !== 'SALE' || !this.sourceRules.length) return null;
        const seen = new Set<string>();
        for (const rule of this.sourceRules) {
            if (!rule.source_id) return 'Selecciona un origen para cada regla por proveedor.';
            if (seen.has(rule.source_id)) return 'No puedes repetir el mismo proveedor dentro de la lista.';
            seen.add(rule.source_id);
        }
        return null;
    }

    private sourceRulePayload(rule: PriceListSourceRule): PriceListSourceRulePayload {
        return {
            source_id: rule.source_id,
            pricing_mode: rule.pricing_mode,
            base_source: rule.base_source,
            adjustment_value: Number(rule.adjustment_value || 0),
            rounding_step: Number(rule.rounding_step || 0),
            min_margin_percent: rule.min_margin_percent == null ? null : Number(rule.min_margin_percent)
        };
    }

    private sourceRuleRequests(priceListId: string) {
        return [
            ...Array.from(this.removedSourceRuleIds).map((ruleId) => this.priceListService.deleteSourceRule(priceListId, ruleId)),
            ...this.sourceRules.map((rule) => {
                const payload = this.sourceRulePayload(rule);
                return rule.id
                    ? this.priceListService.updateSourceRule(priceListId, rule.id, payload)
                    : this.priceListService.saveSourceRule(priceListId, payload);
            })
        ];
    }

    variantsFor(productId: string): Product['variants'] {
        return this.products.find((product) => product.id === productId)?.variants || [];
    }

    onSubmit() {
        if (this.priceListForm.invalid) return;
        const sourceRuleError = this.validateSourceRules();
        if (sourceRuleError) {
            Swal.fire('Revisa las reglas', sourceRuleError, 'warning');
            return;
        }

        this.loading = true;
        const formVal = this.priceListForm.value;

        if (this.isEditMode && this.priceListId) {
            this.priceListService.updatePriceList(this.priceListId, {
                name: formVal.name,
                type: formVal.type,
                currency: formVal.currency,
                    active: formVal.active,
                source_id: formVal.source_id || null,
                pricing_mode: formVal.pricing_mode,
                base_source: formVal.base_source,
                adjustment_value: Number(formVal.adjustment_value || 0),
                rounding_step: Number(formVal.rounding_step || 0),
                min_margin_percent: formVal.min_margin_percent === '' ? null : formVal.min_margin_percent
                }).subscribe({
                next: () => {
                    const itemRequests = [
                        ...Array.from(this.removedItemIds).map((itemId) => this.priceListService.deletePriceListItem(this.priceListId!, itemId)),
                        ...this.items.controls.map((control) => {
                            const value = control.value;
                            const payload = {
                                product_id: value.product_id,
                                variant_id: value.variant_id || null,
                                min_quantity: value.min_quantity || 0,
                                price: value.price === '' ? null : value.price
                            };
                            return value.id
                                ? this.priceListService.updatePriceListItem(this.priceListId!, value.id, payload)
                                : this.priceListService.addPriceListItem(this.priceListId!, payload);
                        }),
                        ...this.sourceRuleRequests(this.priceListId!)
                    ];
                    forkJoin(itemRequests.length ? itemRequests : [of(null)]).subscribe({
                        next: () => {
                            this.loading = false;
                            Swal.fire('Guardado', 'Lista de precios actualizada correctamente.', 'success').then(() => this.router.navigate(['/purchasing/pricelists']));
                        },
                        error: (err) => {
                            this.loading = false;
                            Swal.fire('Error', 'La lista se guardó, pero no se pudieron guardar todos los precios: ' + (err.error?.detail || err.message), 'error');
                        }
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo actualizar: ' + (err.error?.detail || err.message), 'error');
                }
            });
        } else {
            this.priceListService.createPriceList(formVal).subscribe({
                next: (created) => {
                    const ruleRequests = this.sourceRuleRequests(created.id);
                    forkJoin(ruleRequests.length ? ruleRequests : [of(null)]).subscribe({
                        next: () => {
                            this.loading = false;
                            Swal.fire('Creado', 'Lista de precios creada correctamente.', 'success').then(() => {
                                this.router.navigate(['/purchasing/pricelists']);
                            });
                        },
                        error: (err) => {
                            this.loading = false;
                            Swal.fire('Advertencia', 'La lista se creó, pero no se pudieron guardar todas las reglas por proveedor: ' + (err.error?.detail || err.message), 'warning');
                        }
                    });
                },
                error: (err) => {
                    this.loading = false;
                    Swal.fire('Error', 'No se pudo crear: ' + (err.error?.detail || err.message), 'error');
                }
            });
        }
    }

    applyGlobalAdjustment(): void {
        if (!this.priceListId || this.priceListForm.get('type')?.value !== 'SALE') return;
        if (!Number.isFinite(this.globalPercent)) return;
        this.loading = true;
        this.priceListService.applyGlobalAdjustment(this.priceListId, {
            percent: this.globalPercent,
            base_source: this.globalBaseSource,
            preserve_overrides: this.preserveOverrides,
            rounding_step: Number(this.priceListForm.get('rounding_step')?.value || 0),
            min_margin_percent: this.priceListForm.get('min_margin_percent')?.value ?? undefined
        }).subscribe({
            next: (updated) => {
                this.loading = false;
                this.priceListForm.patchValue({
                    pricing_mode: updated.pricing_mode,
                    base_source: updated.base_source,
                    adjustment_value: updated.adjustment_value
                });
                Swal.fire('Regla aplicada', `Se aplicó un aumento global del ${this.globalPercent}%.`, 'success');
            },
            error: (err) => {
                this.loading = false;
                Swal.fire('Error', err.error?.detail || 'No se pudo aplicar el aumento global.', 'error');
            }
        });
    }

    downloadExcel(): void {
        if (!this.priceListId) return;
        this.priceListService.exportPriceList(this.priceListId).subscribe({
            next: (blob) => {
                const url = URL.createObjectURL(blob);
                const anchor = document.createElement('a');
                anchor.href = url;
                anchor.download = `lista-precios-${this.priceListId}.xlsx`;
                anchor.click();
                URL.revokeObjectURL(url);
            },
            error: (err) => Swal.fire('Error', err.error?.detail || 'No se pudo descargar el Excel.', 'error')
        });
    }

    onExcelSelected(event: Event): void {
        const input = event.target as HTMLInputElement;
        this.selectedFile = input.files?.[0] || null;
        this.importResult = null;
        if (!this.selectedFile || !this.priceListId) return;
        this.importing = true;
        this.priceListService.importPriceList(this.priceListId, this.selectedFile, true).subscribe({
            next: (result) => {
                this.importing = false;
                this.importResult = result;
                if (result.rows_failed) {
                    Swal.fire('Revisa el archivo', `${result.rows_failed} fila(s) tienen errores. No se aplicó ningún cambio.`, 'warning');
                    return;
                }
                Swal.fire({
                    title: '¿Aplicar precios?',
                    text: `${result.rows_received} fila(s) serán procesadas. Las celdas vacías quitarán el precio manual y dejarán actuar la regla global.`,
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Aplicar',
                    cancelButtonText: 'Cancelar'
                }).then((answer) => {
                    if (!answer.isConfirmed || !this.selectedFile) return;
                    this.importing = true;
                    this.priceListService.importPriceList(this.priceListId!, this.selectedFile, false).subscribe({
                        next: (applied) => {
                            this.importing = false;
                            this.importResult = applied;
                            Swal.fire('Importado', `${applied.rows_applied} precio(s) aplicados correctamente.`, 'success');
                            this.loadPriceList(this.priceListId!);
                        },
                        error: (err) => {
                            this.importing = false;
                            Swal.fire('Error', err.error?.detail || 'No se pudo aplicar el Excel.', 'error');
                        }
                    });
                });
            },
            error: (err) => {
                this.importing = false;
                Swal.fire('Error', err.error?.detail || 'No se pudo validar el Excel.', 'error');
            }
        });
        input.value = '';
    }
}

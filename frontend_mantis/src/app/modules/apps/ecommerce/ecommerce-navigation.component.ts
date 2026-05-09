import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin, of } from 'rxjs';
import { switchMap } from 'rxjs/operators';

import { EcommerceContextService } from 'src/app/core/services/ecommerce-context.service';
import { PermissionService } from 'src/app/core/services/permission.service';
import { StoreCollection, StoreNavigationItem, Storefront, StorefrontAdminService } from 'src/app/core/services/storefront-admin.service';
import { SweetAlertService } from 'src/app/theme/shared/services/sweet-alert.service';

type NavigationTypeOption = {
  value: string;
  label: string;
  description: string;
};

type NavigationChildDraft = Partial<StoreNavigationItem> & {
  temp_id: string;
};

@Component({
  selector: 'app-ecommerce-navigation',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ecommerce-navigation.component.html',
  styleUrls: ['./ecommerce-shared.component.scss', './ecommerce-navigation.component.scss']
})
export class EcommerceNavigationComponent implements OnInit {
  private storefrontService = inject(StorefrontAdminService);
  private context = inject(EcommerceContextService);
  private permissions = inject(PermissionService);
  private swal = inject(SweetAlertService);

  loading = false;
  saving = false;
  storefronts: Storefront[] = [];
  selectedStorefrontId = '';
  collections: StoreCollection[] = [];
  navigationItems: StoreNavigationItem[] = [];
  filterQuery = '';
  filterType = '';
  form: Partial<StoreNavigationItem> = this.createForm();
  childItems: NavigationChildDraft[] = [];
  editingId = '';
  showEditor = false;
  readonly navigationTypes: NavigationTypeOption[] = [
    { value: 'group', label: 'Grupo desplegable', description: 'Sirve como item padre para agrupar hijos dentro del menu.' },
    { value: 'collection', label: 'Coleccion', description: 'Enlaza a una coleccion visible del storefront.' },
    { value: 'url', label: 'Enlace directo', description: 'Dirige a una ruta interna del storefront o a un enlace externo.' }
  ];

  ngOnInit(): void {
    if (!this.permissions.hasPermission('manage_company')) {
      this.swal.error('Sin permiso', 'No puedes administrar ecommerce.');
      return;
    }
    this.loadData();
  }

  loadData(): void {
    this.loading = true;
    this.storefrontService.getStorefronts().subscribe({
      next: (storefronts) => {
        this.storefronts = storefronts;
        this.selectedStorefrontId = this.context.resolveSelectedStorefront(storefronts);
        this.loadNavigationData();
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar el menu ecommerce.');
      }
    });
  }

  onStorefrontChange(): void {
    this.context.setSelectedStorefrontId(this.selectedStorefrontId);
    this.resetEditor();
    this.loadNavigationData();
  }

  loadNavigationData(): void {
    if (!this.selectedStorefrontId) {
      this.collections = [];
      this.navigationItems = [];
      this.loading = false;
      return;
    }
    this.loading = true;
    forkJoin({
      collections: this.storefrontService.getCollections(this.selectedStorefrontId),
      navigation: this.storefrontService.getNavigation(this.selectedStorefrontId)
    }).subscribe({
      next: ({ collections, navigation }) => {
        this.collections = collections;
        this.navigationItems = navigation;
        if (this.editingId) {
          const editingItem = navigation.find((item) => item.id === this.editingId);
          this.form = editingItem ? { ...editingItem } : this.createForm();
          this.childItems = editingItem?.item_type === 'group' ? this.mapChildren(editingItem.id) : [];
          this.showEditor = !!editingItem;
        }
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo cargar la navegacion.');
      }
    });
  }

  save(): void {
    if (!this.selectedStorefrontId) return;
    this.saving = true;
    const payload = {
      ...this.form,
      storefront_id: this.selectedStorefrontId,
      label: this.form.label?.trim(),
      url: this.form.url?.trim() || null
    };
    const request = this.editingId
      ? this.storefrontService.updateNavigationItem(this.editingId, payload)
      : this.storefrontService.createNavigationItem(payload);
    request
      .pipe(
        switchMap((savedItem) => {
          if (savedItem.item_type !== 'group') {
            return of(savedItem);
          }

          const childRequests = this.childItems
            .filter((child) => child.label?.trim())
            .map((child, index) => {
              const childPayload: Partial<StoreNavigationItem> = {
                storefront_id: this.selectedStorefrontId,
                parent_id: savedItem.id,
                label: child.label?.trim(),
                item_type: child.item_type || 'collection',
                reference_id: child.item_type === 'collection' ? child.reference_id || null : null,
                url: child.item_type === 'url' ? child.url?.trim() || null : null,
                sort_order: child.sort_order ?? index,
                is_visible: child.is_visible ?? true
              };

              return child.id
                ? this.storefrontService.updateNavigationItem(child.id, childPayload)
                : this.storefrontService.createNavigationItem(childPayload);
            });

          return childRequests.length ? forkJoin(childRequests) : of([]);
        })
      )
      .subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Menu guardado');
        this.resetEditor();
        this.loadNavigationData();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo guardar el menu.');
      }
    });
  }

  edit(item: StoreNavigationItem): void {
    this.editingId = item.id;
    this.form = { ...item };
    this.childItems = item.item_type === 'group' ? this.mapChildren(item.id) : [];
    this.showEditor = true;
  }

  createItem(): void {
    this.resetEditor();
    this.showEditor = true;
  }

  createItemOfType(itemType: string): void {
    this.resetEditor();
    this.form = {
      ...this.createForm(),
      item_type: itemType
    };
    this.onTypeChange();
    this.showEditor = true;
  }

  addChildItem(): void {
    this.childItems = [
      ...this.childItems,
      {
        temp_id: this.createTempId(),
        label: '',
        item_type: 'collection',
        reference_id: null,
        url: '',
        sort_order: this.childItems.length,
        is_visible: true
      }
    ];
  }

  removeChildItem(tempId: string): void {
    const child = this.childItems.find((item) => item.temp_id === tempId);
    if (child?.id) {
      child.is_visible = false;
      return;
    }

    this.childItems = this.childItems.filter((item) => item.temp_id !== tempId);
  }

  restoreChildItem(tempId: string): void {
    const child = this.childItems.find((item) => item.temp_id === tempId);
    if (child) {
      child.is_visible = true;
    }
  }

  async deleteItem(item: StoreNavigationItem): Promise<void> {
    const result = await this.swal.confirm(
      'Eliminar item',
      item.item_type === 'group'
        ? `Se eliminara "${item.label}" y todos sus hijos del menu.`
        : `Se eliminara "${item.label}" del menu.`,
    );
    if (!result.isConfirmed) {
      return;
    }

    this.saving = true;
    this.storefrontService.deleteNavigationItem(item.id).subscribe({
      next: () => {
        this.saving = false;
        this.swal.success('Item eliminado');
        if (this.editingId === item.id) {
          this.resetEditor();
        }
        this.loadNavigationData();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo eliminar el item.');
      }
    });
  }

  deleteCurrentItem(): void {
    const currentItem = this.navigationItems.find((item) => item.id === this.editingId);
    if (!currentItem) {
      return;
    }
    void this.deleteItem(currentItem);
  }

  closeEditor(): void {
    this.resetEditor();
  }

  collectionName(referenceId?: string | null): string {
    return this.collections.find((item) => item.id === referenceId)?.name || referenceId || '-';
  }

  typeTone(itemType?: string | null): string {
    return (
      {
        group: 'indigo',
        collection: 'teal',
        url: 'slate'
      }[itemType || ''] || 'slate'
    );
  }

  typeLabel(itemType?: string | null): string {
    return this.navigationTypes.find((item) => item.value === itemType)?.label || itemType || 'Tipo';
  }

  typeDescription(itemType?: string | null): string {
    return this.navigationTypes.find((item) => item.value === itemType)?.description || 'Configuracion del item de menu.';
  }

  referenceLabel(item: StoreNavigationItem): string {
    if (item.item_type === 'group') {
      return 'Grupo de navegacion';
    }
    if (item.item_type === 'collection') {
      return this.collectionName(item.reference_id);
    }
    if (item.item_type === 'url') {
      return item.url || 'Sin URL';
    }
    return item.reference_id || 'Sin referencia';
  }

  parentLabel(parentId?: string | null): string {
    return this.navigationItems.find((item) => item.id === parentId)?.label || 'Raiz principal';
  }

  get topLevelItems(): StoreNavigationItem[] {
    return this.navigationItems
      .filter((item) => !item.parent_id)
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }

  get filteredNavigationItems(): StoreNavigationItem[] {
    const query = this.filterQuery.trim().toLowerCase();
    return this.navigationItems
      .filter((item) => !this.filterType || item.item_type === this.filterType)
      .filter((item) => {
        if (!query) {
          return true;
        }
        const haystack = [item.label, this.referenceLabel(item), this.parentLabel(item.parent_id), this.typeLabel(item.item_type)]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        return haystack.includes(query);
      })
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }

  childrenOf(parentId: string): StoreNavigationItem[] {
    return this.navigationItems
      .filter((item) => item.parent_id === parentId)
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }

  get visibleItemsCount(): number {
    return this.navigationItems.filter((item) => item.is_visible).length;
  }

  get collectionLinkedCount(): number {
    return this.navigationItems.filter((item) => item.item_type === 'collection').length;
  }

  get activeStorefront(): Storefront | null {
    return this.storefronts.find((item) => item.id === this.selectedStorefrontId) || null;
  }

  get availableParentItems(): StoreNavigationItem[] {
    return this.navigationItems
      .filter((item) => item.id !== this.editingId)
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }

  get childNavigationTypes(): NavigationTypeOption[] {
    return this.navigationTypes.filter((item) => item.value !== 'group');
  }

  get canAssignParent(): boolean {
    return this.form.item_type !== 'group' || !!this.editingId;
  }

  onTypeChange(): void {
    if (this.form.item_type !== 'collection') {
      this.form.reference_id = null;
    }
    if (this.form.item_type !== 'url') {
      this.form.url = '';
    }
    if (this.form.item_type !== 'group') {
      this.childItems = [];
    }
  }

  onChildTypeChange(child: NavigationChildDraft): void {
    if (child.item_type !== 'collection') {
      child.reference_id = null;
    }
    if (child.item_type !== 'url') {
      child.url = '';
    }
  }

  moveItem(item: StoreNavigationItem, direction: 'up' | 'down'): void {
    const siblings = this.navigationItems
      .filter((entry) => (entry.parent_id || null) === (item.parent_id || null))
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
    const currentIndex = siblings.findIndex((entry) => entry.id === item.id);
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (currentIndex < 0 || targetIndex < 0 || targetIndex >= siblings.length) {
      return;
    }

    const target = siblings[targetIndex];
    const currentOrder = item.sort_order || 0;
    const targetOrder = target.sort_order || 0;

    this.saving = true;
    forkJoin([
      this.storefrontService.updateNavigationItem(item.id, { sort_order: targetOrder }),
      this.storefrontService.updateNavigationItem(target.id, { sort_order: currentOrder })
    ]).subscribe({
      next: () => {
        this.saving = false;
        this.loadNavigationData();
      },
      error: (err) => {
        this.saving = false;
        this.swal.error('Error', err?.error?.detail || 'No se pudo reordenar el item.');
      }
    });
  }

  private createForm(): Partial<StoreNavigationItem> {
    return {
      parent_id: null,
      label: '',
      item_type: 'group',
      reference_id: null,
      url: '',
      sort_order: 0,
      is_visible: true
    };
  }

  private resetEditor(): void {
    this.form = this.createForm();
    this.childItems = [];
    this.editingId = '';
    this.showEditor = false;
  }

  private mapChildren(parentId: string): NavigationChildDraft[] {
    return this.childrenOf(parentId).map((child) => ({
      ...child,
      temp_id: child.id
    }));
  }

  private createTempId(): string {
    return `child-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
}

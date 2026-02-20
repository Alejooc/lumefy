import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from '../../core/services/api.service';

export interface PackageType {
    id: string;
    name: string;
    width: number;
    height: number;
    length: number;
    max_weight: number;
}

export interface PickingUpdate {
    sale_item_id: string;
    quantity_picked: number;
}

export interface SalePackage {
    id: string;
    sale_id: string;
    package_type_id?: string;
    tracking_number?: string;
    weight: number;
    shipping_label_url?: string;
    items: SalePackageItem[];
    package_type?: PackageType;
}

export interface SalePackageItem {
    id: string;
    package_id: string;
    sale_item_id: string;
    quantity: number;
    sale_item?: any;
}

export interface CreatePackageRequest {
    sale_id: string;
    package_type_id?: string;
    tracking_number?: string;
    weight: number;
    shipping_label_url?: string;
    items: {
        sale_item_id: string;
        quantity: number;
    }[];
}

@Injectable({
    providedIn: 'root'
})
export class LogisticsService {
    private api = inject(ApiService);
    private basePath = '/logistics';

    // --- Package Types ---
    getPackageTypes(): Observable<PackageType[]> {
        return this.api.get<PackageType[]>(`${this.basePath}/package-types`);
    }

    createPackageType(data: Partial<PackageType>): Observable<PackageType> {
        return this.api.post<PackageType>(`${this.basePath}/package-types`, data);
    }

    updatePackageType(id: string, data: Partial<PackageType>): Observable<PackageType> {
        return this.api.put<PackageType>(`${this.basePath}/package-types/${id}`, data);
    }

    deletePackageType(id: string): Observable<any> {
        return this.api.delete<any>(`${this.basePath}/package-types/${id}`);
    }

    // --- Picking ---
    updatePickingItem(data: PickingUpdate): Observable<boolean> {
        return this.api.post<boolean>(`${this.basePath}/picking/update-item`, data);
    }

    // --- Packages ---
    getPackages(saleId: string): Observable<SalePackage[]> {
        return this.api.get<SalePackage[]>(`${this.basePath}/packages/${saleId}`);
    }

    createPackage(data: CreatePackageRequest): Observable<SalePackage> {
        return this.api.post<SalePackage>(`${this.basePath}/packages`, data);
    }
}

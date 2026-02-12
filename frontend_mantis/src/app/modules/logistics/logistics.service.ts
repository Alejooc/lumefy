import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

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
    sale_item?: any; // To access product details
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
    private http = inject(HttpClient);
    private apiUrl = `${environment.apiUrl}/logistics`;

    getPackageTypes(): Observable<PackageType[]> {
        return this.http.get<PackageType[]>(`${this.apiUrl}/package-types`);
    }

    createPackageType(data: any): Observable<PackageType> {
        return this.http.post<PackageType>(`${this.apiUrl}/package-types`, data);
    }

    updatePickingItem(data: PickingUpdate): Observable<boolean> {
        return this.http.post<boolean>(`${this.apiUrl}/picking/update-item`, data);
    }

    getPackages(saleId: string): Observable<SalePackage[]> {
        return this.http.get<SalePackage[]>(`${this.apiUrl}/packages/${saleId}`);
    }

    createPackage(data: CreatePackageRequest): Observable<SalePackage> {
        return this.http.post<SalePackage>(`${this.apiUrl}/packages`, data);
    }
}

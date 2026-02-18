import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';

export interface LandingHero {
    title: string;
    subtitle: string;
    cta_text: string;
    cta_link: string;
    image_url: string;
}

export interface LandingFeature {
    title: string;
    description: string;
    icon: string;
}

export interface LandingClient {
    name: string;
    logo_url: string;
}

export interface LandingSocial {
    facebook?: string;
    twitter?: string;
    instagram?: string;
    linkedin?: string;
}

export interface LandingContact {
    email: string;
    phone: string;
    address: string;
}

export interface Plan {
    id: string;
    name: string;
    code: string;
    price: number;
    currency: string;
    description: string;
    duration_days: number;
    features: any; // JSON object or array
    limits: any;
}

export interface LandingConfig {
    enabled: boolean;
    hero: LandingHero;
    features: LandingFeature[];
    clients: LandingClient[];
    social: LandingSocial;
    contact: LandingContact;
    pricing_visible: boolean;
    plans?: Plan[];
}

@Injectable({
    providedIn: 'root'
})
export class LandingService {
    private apiUrl = `${environment.apiUrl}/system/landing`;

    constructor(private http: HttpClient) { }

    getLandingConfig(): Observable<LandingConfig> {
        return this.http.get<LandingConfig>(this.apiUrl);
    }

    updateLandingConfig(config: LandingConfig): Observable<LandingConfig> {
        return this.http.put<LandingConfig>(this.apiUrl, config);
    }
}

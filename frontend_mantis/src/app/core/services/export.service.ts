import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Injectable({
    providedIn: 'root'
})
export class ExportService {
    private http = inject(HttpClient);

    /**
     * Triggers a file download from an export endpoint.
     * Opens the URL with the auth token as a query param
     * so the browser handles the file download natively.
     */
    download(endpoint: string, format: 'excel' | 'csv' = 'excel', params: Record<string, string> = {}): void {
        const token = localStorage.getItem('access_token');
        let queryParams = new HttpParams().set('format', format);
        Object.entries(params).forEach(([key, value]) => {
            queryParams = queryParams.set(key, value);
        });

        this.http.get(`${environment.apiUrl}${endpoint}`, {
            headers: token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined,
            params: queryParams,
            observe: 'response',
            responseType: 'blob'
        }).subscribe({
            next: (response) => {
                if (!response.body || response.body.size === 0) {
                    throw new Error('La exportación devolvió un archivo vacío.');
                }
                const filename = this.extractFilename(
                    response.headers.get('Content-Disposition'),
                    `export_${Date.now()}.${format === 'csv' ? 'csv' : 'xlsx'}`
                );
                const objectUrl = URL.createObjectURL(response.body);
                const anchor = document.createElement('a');
                anchor.href = objectUrl;
                anchor.download = filename;
                anchor.style.display = 'none';
                document.body.appendChild(anchor);
                anchor.click();
                anchor.remove();
                window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
            },
            error: (err) => {
                console.error('Export error:', err);
                alert('Error al exportar. Intenta de nuevo.');
            }
        });
    }

    private extractFilename(contentDisposition: string | null, fallback: string): string {
        if (!contentDisposition) {
            return fallback;
        }
        const encoded = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
        if (encoded?.[1]) {
            return decodeURIComponent(encoded[1]);
        }
        const basic = contentDisposition.match(/filename="?([^";]+)"?/i);
        return basic?.[1] || fallback;
    }
}

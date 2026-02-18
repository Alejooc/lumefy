import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

@Injectable({
    providedIn: 'root'
})
export class ExportService {
    /**
     * Triggers a file download from an export endpoint.
     * Opens the URL with the auth token as a query param
     * so the browser handles the file download natively.
     */
    download(endpoint: string, format: 'excel' | 'csv' = 'excel', params: Record<string, string> = {}): void {
        const token = localStorage.getItem('access_token');
        const queryParams = new URLSearchParams({ format, ...params });
        const url = `${environment.apiUrl}${endpoint}?${queryParams.toString()}`;

        // Use fetch + blob for authenticated downloads
        fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => {
                if (!res.ok) throw new Error(`Export failed: ${res.status}`);
                const disposition = res.headers.get('Content-Disposition') || '';
                const match = disposition.match(/filename="?(.+?)"?$/);
                const filename = match ? match[1] : `export_${Date.now()}.${format === 'csv' ? 'csv' : 'xlsx'}`;
                return res.blob().then(blob => ({ blob, filename }));
            })
            .then(({ blob, filename }) => {
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                a.click();
                URL.revokeObjectURL(a.href);
            })
            .catch(err => {
                console.error('Export error:', err);
                alert('Error al exportar. Intenta de nuevo.');
            });
    }
}

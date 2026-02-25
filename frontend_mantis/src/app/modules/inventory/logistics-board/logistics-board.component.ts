import { ChangeDetectorRef, Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { SharedModule } from '../../../theme/shared/shared.module';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';

interface BoardCard {
    id: string;
    short_id: string;
    client_name: string;
    branch_name: string;
    total: number;
    item_count: number;
    created_at: string;
    shipping_address?: string;
    notes?: string;
}

interface BoardColumn {
    key: string;
    label: string;
    icon: string;
    color: string;
    nextStatus?: string;
    nextLabel?: string;
    cards: BoardCard[];
}

type LogisticsBoardResponse = Record<string, BoardCard[]>;

@Component({
    selector: 'app-logistics-board',
    templateUrl: './logistics-board.component.html',
    styleUrls: ['./logistics-board.component.scss'],
    standalone: true,
    imports: [CommonModule, SharedModule]
})
export class LogisticsBoardComponent implements OnInit {
    private api = inject(ApiService);
    private swal = inject(SweetAlertService);
    private router = inject(Router);
    private cdr = inject(ChangeDetectorRef);

    columns: BoardColumn[] = [
        { key: 'CONFIRMED', label: 'Confirmados', icon: 'ti ti-clipboard-check', color: '#4680ff', nextStatus: 'PICKING', nextLabel: 'Iniciar Picking', cards: [] },
        { key: 'PICKING', label: 'En Picking', icon: 'ti ti-package', color: '#e58a00', nextStatus: 'PACKING', nextLabel: 'Listo para Empacar', cards: [] },
        { key: 'PACKING', label: 'Empacando', icon: 'ti ti-box', color: '#2ca87f', nextStatus: 'DISPATCHED', nextLabel: 'Despachar', cards: [] },
        { key: 'DISPATCHED', label: 'Despachados', icon: 'ti ti-truck', color: '#673ab7', nextStatus: 'DELIVERED', nextLabel: 'Entregado', cards: [] }
    ];
    isLoading = false;
    draggedCard: BoardCard | null = null;
    dragSourceColumn = '';

    ngOnInit(): void {
        this.loadBoard();
    }

    loadBoard() {
        this.isLoading = true;
        this.api.get<LogisticsBoardResponse>('/logistics/board').subscribe({
            next: (data) => {
                for (const column of this.columns) {
                    column.cards = data[column.key] || [];
                }
                this.isLoading = false;
                this.cdr.detectChanges();
            },
            error: () => {
                this.isLoading = false;
                this.swal.error('Error', 'No se pudo cargar el tablero');
            }
        });
    }

    moveCard(card: BoardCard, targetStatus: string) {
        this.api.post<unknown>('/logistics/board/move', { sale_id: card.id, status: targetStatus }).subscribe({
            next: () => {
                this.swal.success('Movido', 'Pedido movido correctamente');
                this.loadBoard();
            },
            error: (err: { error?: { detail?: string } }) => {
                this.swal.error('Error', err?.error?.detail || 'No se pudo mover el pedido');
            }
        });
    }

    advanceCard(card: BoardCard, column: BoardColumn) {
        if (!column.nextStatus) return;
        this.swal
            .confirm(column.nextLabel || 'Mover', `Mover pedido #${card.short_id} a "${this.getColumnLabel(column.nextStatus)}"`)
            .then((result) => {
                if (result.isConfirmed && column.nextStatus) {
                    this.moveCard(card, column.nextStatus);
                }
            });
    }

    getColumnLabel(status: string): string {
        const column = this.columns.find((col) => col.key === status);
        return column?.label || status;
    }

    getTotalCount(): number {
        return this.columns.reduce((sum, col) => sum + col.cards.length, 0);
    }

    viewSale(id: string) {
        this.router.navigate(['/sales/view', id]);
    }

    onDragStart(event: DragEvent, card: BoardCard, columnKey: string) {
        this.draggedCard = card;
        this.dragSourceColumn = columnKey;
        if (event.dataTransfer) {
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', card.id);
        }
    }

    onDragOver(event: DragEvent) {
        event.preventDefault();
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'move';
        }
    }

    onDrop(event: DragEvent, targetColumn: BoardColumn) {
        event.preventDefault();
        if (!this.draggedCard || this.dragSourceColumn === targetColumn.key) {
            this.draggedCard = null;
            return;
        }
        this.moveCard(this.draggedCard, targetColumn.key);
        this.draggedCard = null;
    }

    onDragEnd() {
        this.draggedCard = null;
    }
}

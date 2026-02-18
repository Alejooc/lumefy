import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { TourService, TourStep } from '../../../../core/services/tour.service';

@Component({
    selector: 'app-tour-overlay',
    standalone: true,
    imports: [CommonModule],
    template: `
        <!-- Backdrop -->
        <div class="tour-backdrop" *ngIf="isActive" (click)="service.skipTour()"></div>

        <!-- Tooltip -->
        <div class="tour-tooltip" *ngIf="isActive && currentStep"
            [style.top.px]="tooltipTop" [style.left.px]="tooltipLeft"
            [class]="'tour-tooltip tour-pos-' + currentStep.position">

            <div class="tour-tooltip-arrow"></div>

            <div class="tour-tooltip-header">
                <span class="tour-step-count">{{ stepIndex + 1 }} / {{ totalSteps }}</span>
                <button class="tour-close-btn" (click)="service.skipTour()">×</button>
            </div>

            <h6 class="tour-tooltip-title">{{ currentStep.title }}</h6>
            <p class="tour-tooltip-content">{{ currentStep.content }}</p>

            <div class="tour-tooltip-footer">
                <button class="btn btn-sm btn-outline-secondary" (click)="service.skipTour()">Omitir</button>
                <div>
                    <button class="btn btn-sm btn-outline-primary me-1" (click)="service.prevStep()"
                        *ngIf="stepIndex > 0">← Anterior</button>
                    <button class="btn btn-sm btn-primary" (click)="service.nextStep()">
                        {{ stepIndex === totalSteps - 1 ? '¡Listo!' : 'Siguiente →' }}
                    </button>
                </div>
            </div>
        </div>

        <!-- Highlight ring -->
        <div class="tour-highlight" *ngIf="isActive"
            [style.top.px]="highlightTop" [style.left.px]="highlightLeft"
            [style.width.px]="highlightWidth" [style.height.px]="highlightHeight">
        </div>
    `,
    styles: [`
        .tour-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 10000;
            cursor: default;
        }

        .tour-highlight {
            position: fixed;
            z-index: 10001;
            border: 3px solid #4680ff;
            border-radius: 8px;
            box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
            pointer-events: auto; /* Block clicks on target */
            background: transparent;
            cursor: default;
            transition: all 0.3s ease;
        }

        .tour-tooltip {
            position: fixed;
            z-index: 10002; /* Ensure above highlight */
            background: #fff;
            border-radius: 12px;
            padding: 16px;
            min-width: 300px;
            max-width: 380px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.25);
            transition: all 0.3s ease;
        }

        .tour-tooltip-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .tour-step-count {
            font-size: 0.75rem;
            color: #999;
            font-weight: 600;
        }

        .tour-close-btn {
            background: none;
            border: none;
            font-size: 1.25rem;
            color: #999;
            cursor: pointer;
            padding: 0;
            line-height: 1;
        }
        .tour-close-btn:hover { color: #333; }

        .tour-tooltip-title {
            margin: 0 0 6px;
            font-weight: 700;
            color: #333;
        }

        .tour-tooltip-content {
            margin: 0 0 12px;
            font-size: 0.875rem;
            color: #666;
            line-height: 1.5;
        }

        .tour-tooltip-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    `]
})
export class TourOverlayComponent implements OnInit, OnDestroy {
    isActive = false;
    currentStep: TourStep | null = null;
    stepIndex = 0;
    totalSteps = 0;

    tooltipTop = 0;
    tooltipLeft = 0;
    highlightTop = 0;
    highlightLeft = 0;
    highlightWidth = 0;
    highlightHeight = 0;

    private subs: Subscription[] = [];

    constructor(
        public service: TourService,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit(): void {
        // We remove the overflow:hidden lock to allow scrollIntoView to work
        // document.body.classList.add('tour-active'); 

        // Listen to global scroll/resize to keep highlight pinned
        window.addEventListener('scroll', this.updatePosition, true);
        window.addEventListener('resize', this.updatePosition, true);

        this.subs.push(
            this.service.isActive$.subscribe(active => {
                this.isActive = active;
                this.cdr.detectChanges();
            }),
            this.service.currentStep$.subscribe(step => {
                this.currentStep = step;
                if (step) {
                    // Slight delay to allow scrollIntoView to start/finish
                    setTimeout(() => this.positionTooltip(step), 100);
                    setTimeout(() => this.positionTooltip(step), 300);
                    setTimeout(() => this.positionTooltip(step), 500);
                }
                this.cdr.detectChanges();
            }),
            this.service.stepIndex$.subscribe(i => {
                this.stepIndex = i;
                this.cdr.detectChanges();
            }),
            this.service.totalSteps$.subscribe(t => {
                this.totalSteps = t;
                this.cdr.detectChanges();
            })
        );
    }

    ngOnDestroy(): void {
        window.removeEventListener('scroll', this.updatePosition, true);
        window.removeEventListener('resize', this.updatePosition, true);
        this.subs.forEach(s => s.unsubscribe());
    }

    private updatePosition = () => {
        if (this.isActive && this.currentStep) {
            this.positionTooltip(this.currentStep);
        }
    };

    private positionTooltip(step: TourStep): void {
        const el = document.querySelector(step.target);
        if (!el) return;

        const rect = el.getBoundingClientRect();
        const padding = 8;

        // Highlight
        this.highlightTop = rect.top - padding;
        this.highlightLeft = rect.left - padding;
        this.highlightWidth = rect.width + padding * 2;
        this.highlightHeight = rect.height + padding * 2;

        // Tooltip positioning
        const tooltipWidth = 340;
        const gap = 16;

        switch (step.position) {
            case 'bottom':
                this.tooltipTop = rect.bottom + gap;
                this.tooltipLeft = rect.left + rect.width / 2 - tooltipWidth / 2;
                break;
            case 'top':
                this.tooltipTop = rect.top - gap - 180;
                this.tooltipLeft = rect.left + rect.width / 2 - tooltipWidth / 2;
                break;
            case 'right':
                this.tooltipTop = rect.top + rect.height / 2 - 80;
                this.tooltipLeft = rect.right + gap;
                break;
            case 'left':
                this.tooltipTop = rect.top + rect.height / 2 - 80;
                this.tooltipLeft = rect.left - tooltipWidth - gap;
                break;
        }

        // Clamp to viewport
        this.tooltipLeft = Math.max(16, Math.min(this.tooltipLeft, window.innerWidth - tooltipWidth - 16));
        this.tooltipTop = Math.max(16, this.tooltipTop);

        this.cdr.detectChanges();
    }
}

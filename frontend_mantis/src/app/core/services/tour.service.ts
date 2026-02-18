import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface TourStep {
    target: string;       // CSS selector for the element to highlight
    title: string;        // Step title
    content: string;      // Step description
    position: 'top' | 'bottom' | 'left' | 'right';
}

@Injectable({ providedIn: 'root' })
export class TourService {
    private steps: TourStep[] = [];
    private currentStepIndex = -1;

    isActive$ = new BehaviorSubject<boolean>(false);
    currentStep$ = new BehaviorSubject<TourStep | null>(null);
    stepIndex$ = new BehaviorSubject<number>(0);
    totalSteps$ = new BehaviorSubject<number>(0);

    private storageKey = 'lumefy_tour_completed';

    get hasCompletedTour(): boolean {
        return localStorage.getItem(this.storageKey) === 'true';
    }

    startTour(steps: TourStep[]): void {
        this.steps = steps;
        this.currentStepIndex = 0;
        this.totalSteps$.next(steps.length);
        this.isActive$.next(true);
        this.showStep(0);
    }

    nextStep(): void {
        if (this.currentStepIndex < this.steps.length - 1) {
            this.currentStepIndex++;
            this.showStep(this.currentStepIndex);
        } else {
            this.endTour();
        }
    }

    prevStep(): void {
        if (this.currentStepIndex > 0) {
            this.currentStepIndex--;
            this.showStep(this.currentStepIndex);
        }
    }

    endTour(): void {
        this.isActive$.next(false);
        this.currentStep$.next(null);
        this.currentStepIndex = -1;
        localStorage.setItem(this.storageKey, 'true');
    }

    skipTour(): void {
        this.endTour();
    }

    resetTour(): void {
        localStorage.removeItem(this.storageKey);
    }

    private showStep(index: number): void {
        const step = this.steps[index];
        this.currentStep$.next(step);
        this.stepIndex$.next(index);

        // Scroll the target element into view
        setTimeout(() => {
            const el = document.querySelector(step.target);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 100);
    }
}

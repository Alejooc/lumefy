// Angular import
import { Component, OnDestroy, ViewEncapsulation, inject, input, ChangeDetectorRef } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { DOCUMENT } from '@angular/common';

// project import
import { Spinkit } from './spinkits';

@Component({
  selector: 'app-spinner',
  templateUrl: './spinner.component.html',
  styleUrls: ['./spinner.component.scss', './spinkit-css/sk-line-material.scss'],
  encapsulation: ViewEncapsulation.None
})
export class SpinnerComponent implements OnDestroy {
  private cdRef = inject(ChangeDetectorRef);

  private router = inject(Router);
  private document = inject<Document>(DOCUMENT);

  // public props
  isSpinnerVisible = true;
  Spinkit = Spinkit;
  backgroundColor = input('#1890ff');
  spinner = input(Spinkit.skLine);

  // Constructor
  constructor() {
    this.router.events.subscribe(
      (event) => {
        if (event instanceof NavigationStart) {
          this.isSpinnerVisible = true;
          this.cdRef.detectChanges();
        } else if (event instanceof NavigationEnd || event instanceof NavigationCancel || event instanceof NavigationError) {
          this.isSpinnerVisible = false;
          this.cdRef.detectChanges();
        }
      },
      () => {
        this.isSpinnerVisible = false;
        this.cdRef.detectChanges();
      }
    );
  }

  // life cycle event
  ngOnDestroy(): void {
    this.isSpinnerVisible = false;
  }
}

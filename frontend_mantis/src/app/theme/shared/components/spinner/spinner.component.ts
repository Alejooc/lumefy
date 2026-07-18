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
  // A spinner created after the router has already emitted NavigationEnd must
  // start hidden; otherwise it can leave an invisible page beneath a full-screen
  // overlay until the user triggers another UI event.
  isSpinnerVisible = false;
  Spinkit = Spinkit;
  backgroundColor = input('#1890ff');
  spinner = input(Spinkit.skLine);

  // Constructor
  constructor() {
    this.router.events.subscribe(
      (event) => {
        if (event instanceof NavigationStart) {
          this.isSpinnerVisible = true;
          this.cdRef.markForCheck();
        } else if (event instanceof NavigationEnd || event instanceof NavigationCancel || event instanceof NavigationError) {
          this.isSpinnerVisible = false;
          this.cdRef.markForCheck();
        }
      },
      () => {
        this.isSpinnerVisible = false;
        this.cdRef.markForCheck();
      }
    );
  }

  // life cycle event
  ngOnDestroy(): void {
    this.isSpinnerVisible = false;
  }
}

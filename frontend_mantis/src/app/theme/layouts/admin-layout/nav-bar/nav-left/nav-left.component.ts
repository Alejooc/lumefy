// Angular import
import { Component, input, output, inject } from '@angular/core';
import { CommonModule } from '@angular/common'; // Needed for pipes
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Subject, debounceTime, distinctUntilChanged } from 'rxjs';

// project import
import { SharedModule } from 'src/app/theme/shared/shared.module';
import { SearchService, SearchResult } from 'src/app/core/services/search.service';

// icons
import { IconService } from '@ant-design/icons-angular';
import { MenuUnfoldOutline, MenuFoldOutline, SearchOutline, ShoppingCartOutline, UserOutline, FileTextOutline, TeamOutline } from '@ant-design/icons-angular/icons';

@Component({
  selector: 'app-nav-left',
  imports: [SharedModule, CommonModule, FormsModule],
  templateUrl: './nav-left.component.html',
  styleUrls: ['./nav-left.component.scss']
})
export class NavLeftComponent {
  private iconService = inject(IconService);
  private searchService = inject(SearchService);
  private router = inject(Router);

  // public props
  readonly navCollapsed = input.required<boolean>();
  readonly NavCollapse = output();
  readonly NavCollapsedMob = output();

  // Search props
  searchTerm: string = '';
  searchResults: SearchResult | null = null;
  isSearching: boolean = false;
  private searchSubject = new Subject<string>();
  showResults: boolean = false;

  // Constructor
  constructor() {
    this.iconService.addIcon(...[
      MenuUnfoldOutline, MenuFoldOutline, SearchOutline,
      ShoppingCartOutline, UserOutline, FileTextOutline, TeamOutline // Added for search result icons
    ]);

    // Debounce search
    this.searchSubject.pipe(
      debounceTime(300),
      distinctUntilChanged()
    ).subscribe(term => {
      if (term.length >= 2) {
        this.performSearch(term);
      } else {
        this.searchResults = null;
        this.showResults = false;
      }
    });
  }

  // public method
  navCollapse() {
    this.NavCollapse.emit();
  }

  navCollapsedMob() {
    this.NavCollapsedMob.emit();
  }

  // Search Methods
  onSearch(term: string) {
    this.searchTerm = term;
    this.searchSubject.next(term);
    this.showResults = true;
  }

  performSearch(term: string) {
    this.isSearching = true;
    this.searchService.search(term).subscribe({
      next: (res) => {
        this.searchResults = res;
        this.isSearching = false;
      },
      error: () => {
        this.isSearching = false;
        this.searchResults = null;
      }
    });
  }

  navigateTo(url: string) {
    this.showResults = false;
    this.searchTerm = '';
    this.router.navigate([url]);
  }

  closeSearch() {
    setTimeout(() => {
      this.showResults = false;
    }, 200);
  }
}

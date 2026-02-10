import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { Category, CategoryService } from '../category.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';

@Component({
    selector: 'app-category-list',
    standalone: false,
    templateUrl: './category-list.component.html',
    styleUrls: ['./category-list.component.scss']
})
export class CategoryListComponent implements OnInit {
    categories: Category[] = [];
    isLoading = false;

    constructor(
        private categoryService: CategoryService,
        private cdr: ChangeDetectorRef,
        private swal: SweetAlertService
    ) { }

    ngOnInit(): void {
        console.log('CategoryListComponent initialized');
        this.loadCategories();
    }

    loadCategories() {
        this.isLoading = true;
        this.categoryService.getCategories().subscribe({
            next: (data) => {
                this.categories = data;
                this.isLoading = false;
                this.cdr.detectChanges(); // Force UI update
                console.log('Categories loaded:', data.length);
            },
            error: (err) => {
                console.error('Error loading categories', err);
                this.isLoading = false;
                this.cdr.detectChanges();
            }
        });
    }

    deleteCategory(id: string) {
        this.swal.confirmDelete().then((confirmed) => {
            if (confirmed) {
                this.isLoading = true;
                this.categoryService.deleteCategory(id).subscribe({
                    next: () => {
                        this.swal.success('Deleted!', 'Category has been deleted.');
                        this.loadCategories(); // Reload list
                    },
                    error: (err) => {
                        console.error('Error deleting category', err);
                        this.swal.error('Error', 'Could not delete category.');
                        this.isLoading = false;
                        this.cdr.detectChanges();
                    }
                });
            }
        });
    }
}

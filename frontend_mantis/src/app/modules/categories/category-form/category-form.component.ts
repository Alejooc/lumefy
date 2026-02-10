import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { CategoryService } from '../category.service';

@Component({
    selector: 'app-category-form',
    standalone: false,
    templateUrl: './category-form.component.html',
    styleUrls: ['./category-form.component.scss']
})
export class CategoryFormComponent implements OnInit {
    form: FormGroup;
    isEditMode = false;
    categoryId: string | null = null;
    submitted = false;

    constructor(
        private fb: FormBuilder,
        private categoryService: CategoryService,
        private router: Router,
        private route: ActivatedRoute
    ) {
        this.form = this.fb.group({
            name: ['', Validators.required],
            description: ['']
        });
    }

    ngOnInit(): void {
        this.categoryId = this.route.snapshot.paramMap.get('id');
        if (this.categoryId) {
            this.isEditMode = true;
            this.loadCategory(this.categoryId);
        }
    }

    loadCategory(id: string) {
        this.categoryService.getCategory(id).subscribe({
            next: (data) => {
                this.form.patchValue(data);
            },
            error: (err) => console.error('Error loading category', err)
        });
    }

    onSubmit() {
        this.submitted = true;
        if (this.form.invalid) {
            return;
        }

        const categoryData = this.form.value;

        if (this.isEditMode && this.categoryId) {
            this.categoryService.updateCategory(this.categoryId, categoryData).subscribe({
                next: () => {
                    this.router.navigate(['/categories']);
                },
                error: (err) => console.error('Error updating category', err)
            });
        } else {
            this.categoryService.createCategory(categoryData).subscribe({
                next: () => {
                    this.router.navigate(['/categories']);
                },
                error: (err) => console.error('Error creating category', err)
            });
        }
    }

    onCancel() {
        this.router.navigate(['/categories']);
    }
}

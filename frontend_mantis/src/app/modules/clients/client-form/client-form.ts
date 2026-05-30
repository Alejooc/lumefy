import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ClientService } from '../client.service';
import { SweetAlertService } from '../../../theme/shared/services/sweet-alert.service';

@Component({
  selector: 'app-client-form',
  templateUrl: './client-form.html',
  styleUrls: ['./client-form.scss'],
  standalone: false
})
export class ClientFormComponent implements OnInit {
  private readonly taxIdPattern = /^[A-Za-z0-9 ./-]+$/;
  private readonly phonePattern = /^[0-9()+\- ]+$/;
  private fb = inject(FormBuilder);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private clientService = inject(ClientService);
  private swal = inject(SweetAlertService);

  form: FormGroup;
  isEdit = false;
  id: string | null = null;
  isLoading = false;

  constructor() {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
      tax_id: ['', [Validators.maxLength(30), Validators.pattern(this.taxIdPattern)]],
      email: ['', [Validators.email]],
      phone: ['', [Validators.maxLength(25), Validators.pattern(this.phonePattern)]],
      address: ['', [Validators.maxLength(180)]],
      notes: ['', [Validators.maxLength(500)]],
      status: ['active', Validators.required],
      tags: [null],
      credit_limit: [0, [Validators.min(0)]]
    });
  }

  ngOnInit(): void {
    this.id = this.route.snapshot.paramMap.get('id');
    if (this.id) {
      this.isEdit = true;
      this.loadClient(this.id);
    }
  }

  loadClient(id: string) {
    this.isLoading = true;
    this.clientService.getClient(id).subscribe({
      next: (client) => {
        // Ensure tags are handled correctly if they arrive as object
        this.form.patchValue(client);
        this.isLoading = false;
      },
      error: (err) => {
        console.error(err);
        this.swal.error('Error al cargar cliente');
        this.router.navigate(['/clients']);
      }
    });
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading = true;
    const clientData = this.normalizeClientPayload();

    if (this.isEdit && this.id) {
      this.clientService.updateClient(this.id, clientData).subscribe({
        next: () => {
          this.swal.success('Cliente actualizado');
          this.router.navigate(['/clients']);
        },
        error: (err) => {
          console.error(err);
          this.swal.error('Error al actualizar');
          this.isLoading = false;
        }
      });
    } else {
      this.clientService.createClient(clientData).subscribe({
        next: () => {
          this.swal.success('Cliente creado');
          this.router.navigate(['/clients']);
        },
        error: (err) => {
          console.error(err);
          this.swal.error('Error al crear');
          this.isLoading = false;
        }
      });
    }
  }

  private normalizeClientPayload() {
    const raw = this.form.getRawValue();

    return {
      ...raw,
      name: raw.name?.trim(),
      tax_id: raw.tax_id?.trim() || null,
      email: raw.email?.trim() || null,
      phone: raw.phone?.trim() || null,
      address: raw.address?.trim() || null,
      notes: raw.notes?.trim() || null
    };
  }
}

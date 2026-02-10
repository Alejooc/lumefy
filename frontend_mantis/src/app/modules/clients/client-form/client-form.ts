import { Component, OnInit } from '@angular/core';
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
  form: FormGroup;
  isEdit = false;
  id: string | null = null;
  isLoading = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private clientService: ClientService,
    private swal: SweetAlertService
  ) {
    this.form = this.fb.group({
      name: ['', Validators.required],
      tax_id: [''],
      email: ['', [Validators.email]],
      phone: [''],
      address: [''],
      notes: ['']
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
      return;
    }

    this.isLoading = true;
    const clientData = this.form.value;

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
}

import { Component, OnInit, inject } from '@angular/core';

import { FormsModule } from '@angular/forms';
import { LandingService, LandingConfig } from 'src/app/core/services/landing.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-landing-cms',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './landing-cms.html',
  styleUrl: './landing-cms.scss',
})
export class LandingCmsComponent implements OnInit {
  private landingService = inject(LandingService);

  config: LandingConfig;
  isLoading = true;
  activeTab = 'hero';

  // Helper arrays for dynamic fields

  ngOnInit() {
    this.landingService.getLandingConfig().subscribe({
      next: (data) => {
        this.config = data;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        // Init empty config if fail
        this.config = {
          enabled: true,
          hero: { title: '', subtitle: '', cta_text: '', cta_link: '', image_url: '' },
          features: [],
          clients: [],
          social: {},
          contact: { email: '', phone: '', address: '' },
          pricing_visible: true
        };
      }
    });
  }

  saveConfig() {
    this.isLoading = true;
    this.landingService.updateLandingConfig(this.config).subscribe({
      next: (data) => {
        this.config = data;
        this.isLoading = false;
        Swal.fire({
          icon: 'success',
          title: 'Guardado',
          text: 'Landing page actualizada correctamente',
          timer: 1500,
          showConfirmButton: false
        });
      },
      error: () => {
        this.isLoading = false;
        Swal.fire('Error', 'No se pudo actualizar la landing page', 'error');
      }
    });
  }

  addFeature() {
    this.config.features.push({ title: 'Nueva Característica', description: 'Descripción...', icon: 'check-circle' });
  }

  removeFeature(index: number) {
    this.config.features.splice(index, 1);
  }

  addClient() {
    this.config.clients.push({ name: 'Nombre Cliente', logo_url: 'assets/images/logo.png' });
  }

  removeClient(index: number) {
    this.config.clients.splice(index, 1);
  }
}

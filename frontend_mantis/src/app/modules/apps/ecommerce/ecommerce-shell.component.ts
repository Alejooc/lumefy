import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-ecommerce-shell',
  standalone: true,
  imports: [RouterOutlet],
  templateUrl: './ecommerce-shell.component.html',
  styleUrls: ['./ecommerce-shell.component.scss']
})
export class EcommerceShellComponent {
}

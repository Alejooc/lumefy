import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { Branch, BranchService } from '../../core/services/branch.service';
import { ManufacturingOrder, ManufacturingService, Bom } from '../../core/services/manufacturing.service';
import { Product, ProductService } from '../../core/services/product.service';
import { CardComponent } from '../../theme/shared/components/card/card.component';
import { SweetAlertService } from '../../theme/shared/services/sweet-alert.service';

@Component({ selector: 'app-manufacturing', standalone: true, imports: [CommonModule, FormsModule, CardComponent], templateUrl: './manufacturing.component.html' })
export class ManufacturingComponent implements OnInit {
  private manufacturing = inject(ManufacturingService); private productsApi = inject(ProductService); private branchesApi = inject(BranchService); private swal = inject(SweetAlertService);
  products: Product[]=[]; branches: Branch[]=[]; boms: Bom[]=[]; orders: ManufacturingOrder[]=[]; loading=true;
  bom = { product_id: '', quantity: 1, lines: [{ component_id: '', quantity: 1 }] };
  order = { bom_id: '', branch_id: '', quantity: 1 };
  ngOnInit(): void { this.load(); }
  load(): void { this.loading=true; forkJoin({products:this.productsApi.getProducts(), branches:this.branchesApi.getBranches(), boms:this.manufacturing.listBoms(), orders:this.manufacturing.listOrders()}).subscribe({next:r=>{this.products=r.products;this.branches=r.branches;this.boms=r.boms;this.orders=r.orders;this.loading=false;},error:e=>{this.loading=false;this.swal.error('Error',e?.error?.detail||'No se pudo cargar Producción.');}}); }
  addLine(): void { this.bom.lines.push({component_id:'',quantity:1}); }
  removeLine(index:number): void { if(this.bom.lines.length>1)this.bom.lines.splice(index,1); }
  createBom(): void { if(!this.bom.product_id||this.bom.lines.some(x=>!x.component_id||x.quantity<=0))return; this.manufacturing.createBom(this.bom).subscribe({next:b=>{this.boms.unshift(b);this.bom={product_id:'',quantity:1,lines:[{component_id:'',quantity:1}]};this.swal.success('Lista de materiales creada');},error:e=>this.swal.error('Error',e?.error?.detail||'No se pudo crear la BOM.')}); }
  createOrder(): void { if(!this.order.bom_id||!this.order.branch_id||this.order.quantity<=0)return; this.manufacturing.createOrder(this.order).subscribe({next:o=>{this.orders.unshift(o);this.swal.success('Orden de fabricación creada');},error:e=>this.swal.error('Error',e?.error?.detail||'No se pudo crear la orden.')}); }
  complete(order:ManufacturingOrder): void { this.manufacturing.completeOrder(order.id).subscribe({next:updated=>{Object.assign(order,updated);this.swal.success('Producción completada');},error:e=>this.swal.error('No se pudo completar',e?.error?.detail||'Revisa los componentes disponibles.')}); }
  confirm(order:ManufacturingOrder): void { this.manufacturing.confirmOrder(order.id).subscribe({next:updated=>{Object.assign(order,updated);this.swal.success('Componentes reservados');},error:e=>this.swal.error('No se pudo confirmar',e?.error?.detail||'Revisa el inventario.')}); }
  cancel(order:ManufacturingOrder): void { this.manufacturing.cancelOrder(order.id).subscribe({next:updated=>{Object.assign(order,updated);this.swal.success('Orden cancelada');},error:e=>this.swal.error('No se pudo cancelar',e?.error?.detail||'')}); }
  productName(id:string):string { return this.products.find(x=>x.id===id)?.name||id; }
  orderProductName(order: ManufacturingOrder): string {
    const bom = this.boms.find(item => item.id === order.bom_id);
    return bom ? this.productName(bom.product_id) : 'BOM no encontrada';
  }
  branchName(branchId: string): string { return this.branches.find(item => item.id === branchId)?.name || 'Sucursal no encontrada'; }
}

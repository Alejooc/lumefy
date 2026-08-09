import { TestBed } from '@angular/core/testing';
import { ClientsModule } from '../clients-module';
import { ClientFormComponent } from './client-form';

describe('ClientFormComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ClientsModule] }).compileComponents();
  });

  it('is declared by the clients feature module', () => {
    expect(ClientFormComponent).toBeDefined();
  });
});

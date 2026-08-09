import { TestBed } from '@angular/core/testing';
import { ClientsModule } from '../clients-module';
import { ClientListComponent } from './client-list';

describe('ClientListComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [ClientsModule] }).compileComponents();
  });

  it('is declared by the clients feature module', () => {
    expect(ClientListComponent).toBeDefined();
  });
});

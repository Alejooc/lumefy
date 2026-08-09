import { TestBed } from '@angular/core/testing';
import { UsersModule } from '../users-module';
import { UserFormComponent } from './user-form';

describe('UserFormComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [UsersModule] }).compileComponents();
  });

  it('is declared by the users feature module', () => {
    expect(UserFormComponent).toBeDefined();
  });
});

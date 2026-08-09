import { TestBed } from '@angular/core/testing';
import { UsersModule } from '../users-module';
import { UserListComponent } from './user-list';

describe('UserListComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [UsersModule] }).compileComponents();
  });

  it('is declared by the users feature module', () => {
    expect(UserListComponent).toBeDefined();
  });
});

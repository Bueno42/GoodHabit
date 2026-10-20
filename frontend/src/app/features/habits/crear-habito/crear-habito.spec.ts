import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CrearHabitoComponent } from './crear-habito.component';

describe('CrearHabito', () => {
  let component: CrearHabitoComponent;
  let fixture: ComponentFixture<CrearHabitoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CrearHabitoComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CrearHabitoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

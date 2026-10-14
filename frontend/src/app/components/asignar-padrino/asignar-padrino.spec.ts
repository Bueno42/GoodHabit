import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AsignarPadrino } from './asignar-padrino';

describe('AsignarPadrino', () => {
  let component: AsignarPadrino;
  let fixture: ComponentFixture<AsignarPadrino>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AsignarPadrino],
    }).compileComponents();

    fixture = TestBed.createComponent(AsignarPadrino);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

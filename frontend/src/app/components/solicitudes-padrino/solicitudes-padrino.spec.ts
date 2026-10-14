import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SolicitudesPadrino } from './solicitudes-padrino';

describe('SolicitudesPadrino', () => {
  let component: SolicitudesPadrino;
  let fixture: ComponentFixture<SolicitudesPadrino>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SolicitudesPadrino],
    }).compileComponents();

    fixture = TestBed.createComponent(SolicitudesPadrino);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

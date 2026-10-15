import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SolicitudesPadrinoComponent } from './solicitudes-padrino.component';

describe('SolicitudesPadrino', () => {
  let component: SolicitudesPadrinoComponent;
  let fixture: ComponentFixture<SolicitudesPadrinoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SolicitudesPadrinoComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(SolicitudesPadrinoComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AsignarPadrinoComponent } from './asignar-padrino.component';

describe('AsignarPadrino', () => {
  let component: AsignarPadrinoComponent;
  let fixture: ComponentFixture<AsignarPadrinoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AsignarPadrinoComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(AsignarPadrinoComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

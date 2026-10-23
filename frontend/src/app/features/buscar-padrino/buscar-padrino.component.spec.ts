import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BuscarPadrinoComponent } from './buscar-padrino.component';

describe('BuscarPadrino', () => {
  let component: BuscarPadrinoComponent;
  let fixture: ComponentFixture<BuscarPadrinoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BuscarPadrinoComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(BuscarPadrinoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

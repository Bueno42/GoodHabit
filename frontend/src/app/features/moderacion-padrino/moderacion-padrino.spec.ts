import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ModeracionPadrinoComponent } from './moderacion-padrino.component';

describe('ModeracionPadrino', () => {
  let component: ModeracionPadrinoComponent;
  let fixture: ComponentFixture<ModeracionPadrinoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ModeracionPadrinoComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ModeracionPadrinoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { App } from './app';
import { routes } from './app.routes';

describe('App', () => {
  beforeEach(async () => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideHttpClient(), provideRouter(routes)],
    }).compileComponents();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.brand')?.textContent).toContain('GoodHabit');
  });

  it('shows only icons in the mobile navigation while retaining accessible names', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const items = fixture.nativeElement.querySelectorAll('.mobile-bottom-nav .mobile-nav-item');

    expect(items).toHaveLength(5);
    items.forEach((item: HTMLElement) => {
      expect(item.querySelector('.mobile-nav-icon')).toBeTruthy();
      expect(item.getAttribute('aria-label')).toBeTruthy();
      expect(item.querySelector(':scope > span:not(.mobile-nav-icon):not(.mobile-nav-badge)')).toBeNull();
    });
  });

  it('keeps configuration open until its closing animation finishes', () => {
    const app = TestBed.createComponent(App).componentInstance;
    app.configuracionAbierta = true;

    app.cerrarConfiguracion();

    expect(app.configuracionAbierta).toBe(true);
    expect(app.configuracionCerrando).toBe(true);

    app.finalizarCierreConfiguracion();

    expect(app.configuracionAbierta).toBe(false);
    expect(app.configuracionCerrando).toBe(false);
  });
});

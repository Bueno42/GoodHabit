import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing'; // Obligatorio
import { PadrinosService } from './padrinos.service';

describe('PadrinosService', () => {
  let service: PadrinosService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule] // Proveedor del mock HTTP
    });
    service = TestBed.inject(PadrinosService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
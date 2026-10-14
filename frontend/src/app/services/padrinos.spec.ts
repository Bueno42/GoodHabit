import { TestBed } from '@angular/core/testing';

import { Padrinos } from './padrinos';

describe('Padrinos', () => {
  let service: Padrinos;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(Padrinos);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});

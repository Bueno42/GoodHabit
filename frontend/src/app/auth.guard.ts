import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

export const authGuard: CanActivateFn = () => {
  if (localStorage.getItem('access_token')) {
    return true;
  }

  return inject(Router).createUrlTree(['/login']);
};

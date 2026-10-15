import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // 1. Buscamos el token en la memoria del navegador
  const token = localStorage.getItem('access_token');

  // 2. Si existe, clonamos la petición original y le inyectamos la cabecera
  if (token) {
    const authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(authReq); // La petición viaja con el DNI en la mano
  }

  // 3. Si no hay token, la petición viaja pelada (ideal para el endpoint de Login)
  return next(req);
};
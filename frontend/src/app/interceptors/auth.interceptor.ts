import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  // 1. Si la petición va a los servidores de Amazon, la dejamos pasar intacta sin tocarla.
  // Esto es crítico para no romper las URLs prefirmadas de S3.
  if (req.url.includes('amazonaws.com')) {
    return next(req);
  }

  // 2. Buscamos el token en la memoria del navegador para las peticiones a nuestro backend
  const token = localStorage.getItem('access_token');

  // 3. Si existe, clonamos la petición original y le inyectamos la cabecera
  if (token) {
    const authReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(authReq); 
  }

  return next(req);
};
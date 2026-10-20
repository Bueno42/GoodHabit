import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Router, ActivatedRoute } from '@angular/router';
import { V1Service } from '../../../api/api/v1.service'; 
import { PresignedURLRequest } from '../../../api/model/presignedURLRequest';

@Component({
  selector: 'app-subir-evidencia',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './subir-evidencia.component.html'
})
export class SubirEvidenciaComponent implements OnInit {
  archivoSeleccionado: File | null = null;
  cargando = false;
  estado = '';
  error = '';
  
  habitIdReal!: number;

  private apiService = inject(V1Service);
  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute); // <-- Inyectás el lector de rutas

  ngOnInit() {
    // Extraemos el ID de la URL al inicializar el componente
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.habitIdReal = parseInt(idParam, 10);
    } else {
      this.error = 'No se proporcionó un ID de hábito válido.';
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.archivoSeleccionado = file;
    }
  }

  subirArchivo() {
    if (!this.archivoSeleccionado) {
      this.error = 'Seleccioná una imagen primero.';
      return;
    }

    this.cargando = true;
    this.error = '';
    this.estado = 'Solicitando permiso al servidor...';

    const requestData: PresignedURLRequest = {
      file_name: this.archivoSeleccionado.name,
      file_type: this.archivoSeleccionado.type
    };

    // PASO 1: Pedir la URL prefirmada a Django
    this.apiService.v1S3PresignedUrlCreate(requestData).subscribe({
      next: (s3Data: any) => {
        this.estado = 'Subiendo imagen a AWS S3...';
        
        // PASO 2: Subir archivo directamente a AWS S3
        // IMPORTANTE: Según si en Django usaste generate_presigned_post o generate_presigned_url(ClientMethod='put_object')
        // Asumiremos un PUT directo que es el más estándar para SPAs. Si usaste POST, el código lleva un FormData con los "fields".
        this.http.put(s3Data.upload_url, this.archivoSeleccionado!, {
          headers: { 'Content-Type': this.archivoSeleccionado!.type }
        }).subscribe({
          next: () => {
            this.estado = 'Registrando evidencia en la base de datos...';
            
            // PASO 3: Usamos directamente la file_url que el backend nos preparó
            const urlFinalS3 = s3Data.file_url; 

            this.apiService.v1EvidenciasCreate({
              habit_log: this.habitIdReal,
              s3_file_url: urlFinalS3,
              descripcion: 'Evidencia subida desde Angular'
            }).subscribe({
              next: () => {
                this.cargando = false;
                this.estado = '¡Subida exitosa!';
                setTimeout(() => this.router.navigate(['/dashboard']), 1500);
              },
              error: (err) => this.manejarError('Error al guardar en la base de datos', err)
            });
          },
          error: (err) => this.manejarError('AWS S3 rechazó el archivo. Revisá permisos CORS de tu bucket.', err)
        });
      },
      error: (err) => this.manejarError('Django denegó la URL prefirmada.', err)
    });
  }

  manejarError(mensaje: string, err: any) {
    console.error(err);
    this.error = mensaje;
    this.cargando = false;
    this.estado = '';
  }
}
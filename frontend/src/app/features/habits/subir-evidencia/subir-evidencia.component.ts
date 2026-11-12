import { Component, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, ActivatedRoute } from '@angular/router';
import { V1Service } from '../../../api/api/v1.service';
import { PresignedURLRequest } from '../../../api/model/presignedURLRequest';
import { FileTypeEnum } from '../../../api/model/fileTypeEnum';

interface PresignedPostResponse {
  upload_url: string;
  fields: Record<string, string>;
  file_url: string;
  key: string;
}

@Component({
  selector: 'app-subir-evidencia',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './subir-evidencia.component.html'
})
export class SubirEvidenciaComponent implements OnInit {
  archivoSeleccionado: File | null = null;
  descripcion = '';
  cargando = false;
  cancelando = false;
  estado = '';
  error = '';

  habitLogId!: number;

  private apiService = inject(V1Service);
  private http = inject(HttpClient);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  ngOnInit() {
    const idParam = this.route.snapshot.paramMap.get('id');
    if (idParam) {
      this.habitLogId = parseInt(idParam, 10);
    } else {
      this.error = 'No se proporcionó un ID de registro válido.';
    }
  }

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.archivoSeleccionado = file;
      this.error = '';
    }
  }

  subirArchivo() {
    if (!this.archivoSeleccionado) {
      this.error = 'Seleccioná una imagen o video primero.';
      return;
    }

    const mimeSeleccionado = this.archivoSeleccionado.type;
    const tiposPermitidos = Object.values(FileTypeEnum) as string[];

    if (!tiposPermitidos.includes(mimeSeleccionado)) {
      this.error = `Formato no soportado (${mimeSeleccionado || 'desconocido'}). Subí JPEG, PNG o MP4.`;
      return;
    }

    this.cargando = true;
    this.error = '';
    this.estado = 'Solicitando permiso al servidor...';

    const requestData: PresignedURLRequest = {
      file_name: this.archivoSeleccionado.name,
      file_type: mimeSeleccionado as FileTypeEnum
    };

    this.apiService.v1S3PresignedUrlCreate(requestData).subscribe({
      next: (s3Data: PresignedPostResponse) => {
        this.estado = 'Subiendo archivo a AWS S3...';

        const formData = new FormData();
        Object.entries(s3Data.fields).forEach(([key, value]) => formData.append(key, value));
        formData.append('file', this.archivoSeleccionado!);

        this.http.post(s3Data.upload_url, formData).subscribe({
          next: () => {
            this.estado = 'Registrando evidencia en la base de datos...';

            this.apiService.v1EvidenciasCreate({
              habit_log: this.habitLogId,
              s3_file_url: s3Data.file_url,
              descripcion: this.descripcion.trim() || 'Evidencia adjuntada'
            }).subscribe({
              next: () => {
                this.cargando = false;
                this.estado = '¡Subida exitosa!';
                setTimeout(() => this.router.navigate(['/dashboard']), 1200);
              },
              error: (err) => this.manejarError('Error al guardar en la base de datos.', err)
            });
          },
          error: (err) => this.manejarError('AWS S3 rechazó el archivo. Revisá permisos CORS de tu bucket.', err)
        });
      },
      error: (err) => this.manejarError('Django denegó la URL prefirmada.', err)
    });
  }

  cancelarRegistro() {
    if (this.cargando || this.cancelando || !this.habitLogId) return;

    this.cancelando = true;
    this.apiService.v1LogsDestroy(this.habitLogId).subscribe({
      next: () => {
        this.cancelando = false;
        this.router.navigate(['/dashboard']);
      },
      error: () => {
        // Si ya tenía evidencia previa (reintento) o no se pudo borrar, volvemos igual sin bloquear al usuario
        this.cancelando = false;
        this.router.navigate(['/dashboard']);
      }
    });
  }

  manejarError(mensaje: string, err: any) {
    console.error(err);
    this.error = mensaje;
    this.cargando = false;
    this.estado = '';
  }
}
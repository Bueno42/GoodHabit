import uuid
import logging
import boto3
from botocore.config import Config
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024

def generar_presigned_url_s3(file_name, file_type):
    """
    Genera una presigned url para la subida directa a AWS S3 y
    retorna la URL persistente que se guardara en la base de datos
    """
    

    s3_client = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com",
        config=Config(signature_version='s3v4')
    )

    #Evitamos colisiones de nombres generando un UUID unico
    # UUID(Universally Unique Identifier) es un codigo estandar de 128 bits diseñado
    # para identificar informacion en sistemas sin necesidad de una autoridad central

    ext= file_name.split('.')[-1] if '.' in file_name else ''
    unique_key = f"evidencias/{uuid.uuid4()}.{ext}" if ext else f"evidencias/{uuid.uuid4()}"

    try:
        # A POST policy can enforce a content-length range in S3.
        presigned_post = s3_client.generate_presigned_post(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=unique_key,
            Fields={'Content-Type': file_type},
            Conditions=[
                {'Content-Type': file_type},
                ['content-length-range', 0, MAX_UPLOAD_SIZE],
            ],
            ExpiresIn=3600,
        )

        # URL publica que se guarda como VARCHAR
        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{unique_key}"

        return {
            'upload_url': presigned_post['url'],
            'fields': presigned_post['fields'],
            'file_url': file_url,
            'key': unique_key
        }
    except Exception:
        logger.exception("Error al generar presigned URL")
        return None

import uuid
import logging
import boto3
from urllib.parse import urlparse, unquote
from botocore.exceptions import ClientError
from botocore.config import Config
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def obtener_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
        endpoint_url=f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com",
        config=Config(signature_version='s3v4')
    )


def generar_presigned_url_s3(file_name, file_type):
    """
    Genera una Presigned POST URL para que el frontend suba la evidencia a S3.
    """
    s3_client = obtener_s3_client()
    ext = file_name.split('.')[-1] if '.' in file_name else ''
    unique_filename = f"{uuid.uuid4()}.{ext}" if ext else str(uuid.uuid4())
    object_key = f"evidencias/{unique_filename}"

    try:
        response = s3_client.generate_presigned_post(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=object_key,
            Fields={"Content-Type": file_type},
            Conditions=[
                {"Content-Type": file_type},
                ["content-length-range", 1, MAX_UPLOAD_SIZE],
            ],
            ExpiresIn=3600
        )
        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{object_key}"
        return {
            "upload_url": response["url"],
            "fields": response["fields"],
            "file_url": file_url,
            "key": object_key,
        }
    except ClientError as e:
        logger.error(f"Error generando presigned POST en S3: {e}")
        return None


def generar_presigned_url_lectura(s3_url_or_key, expiracion=900):
    """
    Recibe la key o la URL completa de S3 y devuelve una Presigned URL temporal GET.
    """
    if not s3_url_or_key:
        return None

    if s3_url_or_key.startswith('http'):
        parsed = urlparse(s3_url_or_key)
        # Decodificamos %20 u otros caracteres URL-encoded para obtener la Key real de S3
        key = unquote(parsed.path.lstrip('/'))
        bucket_prefix = f"{settings.AWS_STORAGE_BUCKET_NAME}/"
        if key.startswith(bucket_prefix):
            key = key[len(bucket_prefix):]
    else:
        key = unquote(s3_url_or_key.lstrip('/'))

    s3_client = obtener_s3_client()
    try:
        url_temporal = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': key,
            },
            ExpiresIn=expiracion
        )
        return url_temporal
    except ClientError as e:
        logger.error(f"Error generando presigned GET en S3: {e}")
        return None
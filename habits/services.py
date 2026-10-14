import uuid
import boto3
from botocore.config import Config
from django.conf import settings

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
        config=Config(signature_version='s3v4')
    )

    #Evitamos colisiones de nombres generando un UUID unico
    # UUID(Universally Unique Identifier) es un codigo estandar de 128 bits diseñado
    # para identificar informacion en sistemas sin necesidad de una autoridad central

    ext= file_name.split('.')[-1] if '.' in file_name else ''
    unique_key = f"evidencias/{uuid.uuid4()}.{ext}" if ext else f"evidencias/{uuid.uuid4()}"

    try:
        # Generamos una URL temporal de subida (PUT)
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': unique_key,
                'ContentType': file_type,
            },
            ExpiresIn=3600  #Valido por 1 hora
        )

        # URL publica que se guarda como VARCHAR
        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{unique_key}"

        return {
            'upload_url': presigned_url,
            'file_url': file_url,
            'key': unique_key
        }
    except Exception as e:
        print(f"Error al generar presigned URL: {e}")
        return None



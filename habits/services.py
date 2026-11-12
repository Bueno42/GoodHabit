import uuid
import logging
import boto3
from datetime import timedelta
from urllib.parse import urlparse, unquote
from botocore.exceptions import ClientError
from botocore.config import Config
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .models import Habit, HabitLog

logger = logging.getLogger(__name__)

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def filtro_logs_completos_q(prefijo: str = '') -> Q:
    """
    Regla de integridad (Sección 4.7):
    - Si el hábito es Gratuito (is_premium=False), basta la autodeclaración (no requiere S3).
    - Si el hábito es Desafío Premium (is_premium=True), exige que la evidencia en S3 exista.
    """
    campo_premium = f"{prefijo}habit__is_premium" if prefijo else "habit__is_premium"
    campo_evidencia = f"{prefijo}evidencia__isnull" if prefijo else "evidencia__isnull"
    return Q(**{campo_premium: False}) | Q(**{campo_evidencia: False})


def aplicar_timeout_revisiones(habit: Habit = None) -> int:
    """
    Aplica la Regla de Aprobación Automática por Silencio (Timeout 24hs - Sección 4.7)
    mediante evaluación perezosa (Lazy Evaluation), sin requerir workers de Celery.
    """
    limite_24h = timezone.now() - timedelta(hours=24)
    qs = HabitLog.objects.filter(
        estado=HabitLog.Estado.EN_REVISION,
        evidencia__isnull=False,
        fecha_envio__lte=limite_24h,
    )
    if habit is not None:
        qs = qs.filter(habit=habit)

    ahora = timezone.now()
    actualizados = qs.update(
        estado=HabitLog.Estado.TIMEOUT_APROBADO,
        fecha_revision=ahora,
    )
    return actualizados


def calcular_racha_actual(habit: Habit) -> int:
    aplicar_timeout_revisiones(habit)

    condicion_validez = Q(evidencia__isnull=False) if habit.is_premium else Q()
    fechas_aprobadas = set(
        habit.logs.filter(
            condicion_validez,
            estado__in=[HabitLog.Estado.APROBADO, HabitLog.Estado.TIMEOUT_APROBADO],
        ).values_list('date', flat=True)
    )

    if not fechas_aprobadas:
        return 0

    def es_dia_programado(fecha):
        if habit.frequency == Habit.FrequencyType.WEEKDAYS:
            return fecha.weekday() < 5  # Lunes (0) a Viernes (4)
        if habit.frequency == Habit.FrequencyType.WEEKENDS:
            return fecha.weekday() >= 5  # Sábado (5) y Domingo (6)
        return True  # DAILY / CUSTOM

    hoy = timezone.localdate()
    dia_cursor = hoy

    # Si hoy aún no se cumplió (o no tocaba), retrocedemos al último día programado exigible
    if dia_cursor not in fechas_aprobadas:
        dia_cursor -= timedelta(days=1)
        while not es_dia_programado(dia_cursor):
            dia_cursor -= timedelta(days=1)

    racha = 0
    while True:
        if not es_dia_programado(dia_cursor):
            dia_cursor -= timedelta(days=1)
            continue
        if dia_cursor in fechas_aprobadas:
            racha += 1
            dia_cursor -= timedelta(days=1)
        else:
            break

    return racha


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
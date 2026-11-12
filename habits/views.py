from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import viewsets, status, permissions, mixins, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import Habit, HabitLog, HabitPadrino, Evidencia
from .serializers import (
    EvidenciaSerializer,
    PresignedURLSerializer,
    HabitSerializer,
    HabitLogSerializer,
    HabitPadrinoSerializer,
    UserSerializer,
    InvitarPadrinoSerializer,
    RespuestaPadrinoSerializer,
)
from .services import (
    generar_presigned_url_s3,
    aplicar_timeout_revisiones,
    filtro_logs_completos_q,
)

User = get_user_model()


class UserViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return User.objects.none()
        return User.objects.exclude(id=self.request.user.id)


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'], url_path='heatmap')
    def heatmap(self, request, pk=None):
        habit = self.get_object()
        aplicar_timeout_revisiones(habit)
        hoy = timezone.localdate()
        hace_30_dias = hoy - timedelta(days=29)

        qs = habit.logs.filter(date__gte=hace_30_dias)
        if habit.is_premium:
            qs = qs.filter(evidencia__isnull=False)

        logs = qs.values('date', 'estado')
        mapa_logs = {log['date'].isoformat(): log['estado'] for log in logs}

        dias = []
        for i in range(30):
            fecha_iter = hace_30_dias + timedelta(days=i)
            fecha_str = fecha_iter.isoformat()
            dias.append({
                'fecha': fecha_str,
                'estado': mapa_logs.get(fecha_str, 'SIN_REGISTRO')
            })

        return Response(dias)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            aplicar_timeout_revisiones()
            return Habit.objects.filter(user=self.request.user)
        return Habit.objects.none()

    @action(detail=True, methods=['post'], url_path='invitar-padrino')
    def invitar_padrino(self, request, pk=None):
        habit = self.get_object()

        if habit.user != request.user:
            return Response({"detail": "No tenés permiso sobre este hábito."}, status=status.HTTP_403_FORBIDDEN)

        serializer = InvitarPadrinoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        padrino_user = serializer.validated_data['padrino_email']

        try:
            HabitPadrino.objects.create(
                habit=habit,
                padrino=padrino_user,
                estado_invitacion=HabitPadrino.EstadoInvitacion.PENDIENTE
            )
            return Response(
                {"message": f"Invitación enviada a {padrino_user.email}"},
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response({"detail": e.messages[0]}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)


class SolicitudPadrinoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = HabitPadrino.objects.all()
    serializer_class = RespuestaPadrinoSerializer

    @action(detail=True, methods=['post'], url_path='responder')
    def responder_solicitud(self, request, pk=None):
        solicitud = self.get_object()

        if solicitud.padrino != request.user:
            return Response(
                {"detail": "No tenés autorización para responder esta solicitud."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        aceptado = serializer.validated_data['aceptar']
        solicitud.estado_invitacion = (
            HabitPadrino.EstadoInvitacion.ACEPTADO
            if aceptado
            else HabitPadrino.EstadoInvitacion.RECHAZADO
        )
        solicitud.save()

        return Response(
            HabitPadrinoSerializer(solicitud).data,
            status=status.HTTP_200_OK
        )


class HabitPadrinoViewSet(viewsets.ModelViewSet):
    serializer_class = HabitPadrinoSerializer
    permission_classes = [IsAuthenticated]
    queryset = HabitPadrino.objects.all()

    def get_queryset(self):
        user = self.request.user
        return HabitPadrino.objects.filter(
            models.Q(padrino=user) | models.Q(habit__user=user)
        ).select_related('habit', 'padrino').distinct()

    @action(detail=False, methods=['get'], url_path='mis-solicitudes')
    def mis_solicitudes(self, request):
        queryset = HabitPadrino.objects.filter(
            padrino=request.user,
            estado_invitacion=HabitPadrino.EstadoInvitacion.PENDIENTE
        ).select_related('habit', 'padrino')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class HabitLogViewSet(viewsets.ModelViewSet):
    serializer_class = HabitLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = HabitLog.objects.all()

    def create(self, request, *args, **kwargs):
        habit_id = request.data.get('habit')
        log_date = request.data.get('date', timezone.localdate())

        if habit_id:
            try:
                existing_log = HabitLog.objects.get(
                    habit_id=habit_id,
                    date=log_date,
                    habit__user=request.user,
                )
            except (HabitLog.DoesNotExist, TypeError, ValueError, ValidationError):
                pass
            else:
                # Si es un hábito gratuito y había quedado en otro estado, aseguramos APROBADO
                if not existing_log.habit.is_premium and existing_log.estado != HabitLog.Estado.APROBADO:
                    existing_log.estado = HabitLog.Estado.APROBADO
                    existing_log.save(update_fields=['estado'])
                return Response(
                    self.get_serializer(existing_log).data,
                    status=status.HTTP_200_OK,
                )

        return super().create(request, *args, **kwargs)

    def get_queryset(self):
        aplicar_timeout_revisiones()
        qs = HabitLog.objects.filter(habit__user=self.request.user)
        # En 'list' mostramos todos los logs gratuitos y solo los logs premium que ya tienen evidencia en S3
        if self.action == 'list':
            qs = qs.filter(filtro_logs_completos_q())
        return qs.order_by('-date', '-id')

    def perform_create(self, serializer):
        habit = serializer.validated_data['habit']
        if habit.user != self.request.user:
            raise serializers.ValidationError({"detail": "No tenés permiso para registrar ejecuciones en un hábito ajeno."})

        if not habit.is_premium:
            # Modo Gratuito (Sección 4.7): Autodeclaración directa en 1 clic
            estado_inicial = HabitLog.Estado.APROBADO
        else:
            tiene_padrino_activo = HabitPadrino.objects.filter(
                habit=habit,
                estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
            ).exists()
            estado_inicial = HabitLog.Estado.EN_REVISION if tiene_padrino_activo else HabitLog.Estado.APROBADO

        serializer.save(estado=estado_inicial)

    def perform_update(self, serializer):
        log = self.get_object()
        user = self.request.user
        nuevo_estado = serializer.validated_data.get('estado', log.estado)

        if log.habit.user == user and log.estado == HabitLog.Estado.EN_REVISION and nuevo_estado == HabitLog.Estado.APROBADO:
            if HabitPadrino.objects.filter(
                habit=log.habit,
                estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
            ).exists():
                raise serializers.ValidationError({"detail": "No podés auto-aprobar un hábito que requiere revisión de tu padrino."})

        serializer.save()

    @extend_schema(responses=HabitLogSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='pendientes-revision')
    def pendientes_revision(self, request):
        """Lista los registros diarios pendientes de validación para los hábitos donde soy padrino"""
        aplicar_timeout_revisiones()
        logs = HabitLog.objects.filter(
            habit__is_premium=True,
            habit__padrino_assignments__padrino=request.user,
            habit__padrino_assignments__estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO,
            estado=HabitLog.Estado.EN_REVISION,
            evidencia__isnull=False,
        ).distinct().order_by('-date', '-id')
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='moderar')
    def moderar(self, request, pk=None):
        """Permite a un padrino aprobar o rechazar un log"""
        aplicar_timeout_revisiones()
        try:
            log = HabitLog.objects.get(pk=pk)
        except HabitLog.DoesNotExist:
            return Response({'error': 'Registro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        es_padrino = HabitPadrino.objects.filter(
            habit=log.habit,
            padrino=request.user,
            estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
        ).exists()

        if not es_padrino:
            return Response({'error': 'No tenés permisos de moderación sobre este hábito.'}, status=status.HTTP_403_FORBIDDEN)

        if log.estado != HabitLog.Estado.EN_REVISION:
            return Response({'error': f'El registro ya fue procesado y está en estado {log.estado}.'}, status=status.HTTP_400_BAD_REQUEST)

        nuevo_estado = request.data.get('estado')
        motivo = request.data.get('motivo_rechazo', '')

        if nuevo_estado not in [HabitLog.Estado.APROBADO, HabitLog.Estado.RECHAZADO]:
            return Response({'error': 'Estado inválido. Use APROBADO o RECHAZADO.'}, status=status.HTTP_400_BAD_REQUEST)

        if nuevo_estado == HabitLog.Estado.RECHAZADO and not motivo:
            return Response({'error': 'Debe especificar un motivo de rechazo.'}, status=status.HTTP_400_BAD_REQUEST)

        log.estado = nuevo_estado
        log.revisado_por = request.user
        log.fecha_revision = timezone.now()
        log.motivo_rechazo = motivo if nuevo_estado == HabitLog.Estado.RECHAZADO else None
        log.save()

        return Response(HabitLogSerializer(log).data, status=status.HTTP_200_OK)


class PresignedURLView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Generar URL Prefirmada para S3",
        description="Genera una URL temporal de AWS S3 para subir imágenes JPEG/PNG o videos MP4 de hasta 10 MB.",
        request=PresignedURLSerializer,
        responses={
            200: OpenApiResponse(description="Devuelve un JSON con la 'url' prefirmada y los campos necesarios para el upload."),
            400: OpenApiResponse(description="Error de validación si faltan parámetros o el MIME no está permitido.")
        }
    )
    def post(self, request):
        serializer = PresignedURLSerializer(data=request.data)
        if serializer.is_valid():
            file_name = serializer.validated_data['file_name']
            file_type = serializer.validated_data['file_type']

            data = generar_presigned_url_s3(file_name, file_type)
            if data:
                return Response(data, status=status.HTTP_200_OK)
            return Response({"error": "No se pudo generar la URL de S3"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EvidenciaViewSet(viewsets.ModelViewSet):
    serializer_class = EvidenciaSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Evidencia.objects.all()

    def get_queryset(self):
        return Evidencia.objects.filter(usuario=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        habit_log = serializer.validated_data.get('habit_log')
        if habit_log:
            if habit_log.habit.user != request.user:
                return Response(
                    {"detail": "No tenés permiso para adjuntar evidencia a este registro."},
                    status=status.HTTP_403_FORBIDDEN
                )

            tiene_padrino_activo = HabitPadrino.objects.filter(
                habit=habit_log.habit,
                estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
            ).exists()
            nuevo_estado = HabitLog.Estado.EN_REVISION if tiene_padrino_activo else HabitLog.Estado.APROBADO

            habit_log.estado = nuevo_estado
            habit_log.motivo_rechazo = None
            habit_log.fecha_envio = timezone.now()
            habit_log.save(update_fields=['estado', 'motivo_rechazo', 'fecha_envio'])

            existing_evidence = self.get_queryset().filter(habit_log=habit_log).first()
            if existing_evidence:
                serializer.instance = existing_evidence
                serializer.save(usuario=request.user)
                return Response(serializer.data, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)
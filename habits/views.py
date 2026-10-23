import boto3
from rest_framework import viewsets, status, permissions, mixins, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.db import models
from django.contrib.auth import get_user_model
from botocore.exceptions import ClientError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from .models import Evidencia
from .serializers import EvidenciaSerializer, PresignedURLSerializer
from .services import generar_presigned_url_s3
from habits.models import HabitLog, HabitPadrino
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import Habit, HabitLog, HabitPadrino
from .serializers import HabitSerializer, HabitLogSerializer, HabitPadrinoSerializer, UserSerializer

User = get_user_model()

class UserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer 
    
    
    filter_backends = [filters.SearchFilter]
    
    search_fields = ['username']
    
    def get_queryset(self):
        
        return User.objects.exclude(id=self.request.user.id)

class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        # Inyecta el usuario que hizo la petición HTTP (request.user) 
        # directamente en el guardado del serializador.
        serializer.save(user=self.request.user)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Habit.objects.filter(user=self.request.user)
        return Habit.objects.all()

    @action(detail=True, methods=['post'], url_path='invitar-padrino', permission_classes=[AllowAny])
    def invitar_padrino(self, request, pk=None):
        try:
            habito = Habit.objects.get(pk=pk)
            padrino_id = request.data.get('padrino_id')

            if not padrino_id:
                return Response({'detail': 'Debe proporcionar padrino_id'}, status=status.HTTP_400_BAD_REQUEST)

            padrino = User.objects.get(pk=padrino_id)

            if habito.usuario_id == padrino.id:
                return Response({'detail': 'Un usuario no puede ser su propio padrino.'}, status=status.HTTP_400_BAD_REQUEST)

            padrinazgo, created = HabitPadrino.objects.get_or_create(
                habit=habito,
                padrino=padrino,
                defaults={'estado': 'PENDIENTE'}
            )

            if not created:
                return Response({'detail': 'Ya existe una solicitud enviada a este usuario.'}, status=status.HTTP_400_BAD_REQUEST)

            return Response({'detail': 'Invitación enviada exitosamente.'}, status=status.HTTP_201_CREATED)

        except Habit.DoesNotExist:
            return Response({'detail': f'No existe el hábito con ID {pk}. Creá uno antes de probar.'}, status=status.HTTP_404_NOT_FOUND)
        except User.DoesNotExist:
            return Response({'detail': f'No existe el usuario con ID {padrino_id}.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HabitPadrinoViewSet(viewsets.ModelViewSet):
    serializer_class = HabitPadrinoSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return HabitPadrino.objects.filter(padrino=self.request.user)
        return HabitPadrino.objects.all()

    @action(detail=False, methods=['get'], url_path='mis-solicitudes')
    def mis_solicitudes(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class HabitLogViewSet(viewsets.ModelViewSet):
    serializer_class = HabitLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = HabitLog.objects.all()

    def get_queryset(self):
        user = self.request.user
        
        return HabitLog.objects.filter(
            models.Q(habit__user=user) | 
            models.Q(
                habit__padrino_assignments__padrino=user, 
                habit__padrino_assignments__estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
            )
        ).distinct()

    def perform_create(self, serializer):
        habit = serializer.validated_data['habit']
        
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
            if HabitPadrino.objects.filter(habit=log.habit, estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO).exists():
                raise serializers.ValidationError({"detail": "No puedes auto-aprobar un hábito que requiere revisión de tu padrino"})

        
        es_padrino_activo = HabitPadrino.objects.filter(
            habit=log.habit,
            padrino=user,
            estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
        ).exists()

        if es_padrino_activo and log.habit.user != user:
            serializer.save()
        else:
            serializer.save()

    
    @extend_schema(responses=HabitLogSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='pendientes-revision')
    def pendientes_revision(self, request):
        """Lista los registros diarios pendientes de validación para los hábitos donde soy padrino"""
        habitos_supervisados = Habit.objects.filter(
            padrino_assignments__padrino=request.user,
            padrino_assignments__estado_invitacion=HabitPadrino.EstadoInvitacion.ACEPTADO
        )
        logs_pendientes = HabitLog.objects.filter(
            habit__in=habitos_supervisados,
            estado=HabitLog.Estado.EN_REVISION
        )
        serializer = self.get_serializer(logs_pendientes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='moderar')
    def moderar(self, request, pk=None):
        """Permite a un padrino aprobar o rechazar un log"""
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
            return Response({'error': 'No tienes permisos de moderación sobre este hábito.'}, status=status.HTTP_403_FORBIDDEN)

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
        description="Genera una URL temporal de AWS S3 para que el cliente pueda subir directamente la evidencia multimedia.",
        request=PresignedURLSerializer,
        responses={
            200: OpenApiResponse(description="Devuelve un JSON con la 'url' prefirmada y los campos necesarios para el upload."),
            400: OpenApiResponse(description="Error de validación si faltan parámetros.")
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
            return Response({"error:" "No se pudo generar la URL de S3"},  status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        pass

class EvidenciaViewSet(viewsets.ModelViewSet):
    serializer_class = EvidenciaSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = Evidencia.objects.all()

    def get_queryset(self):
        return Evidencia.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):  # CORREGIDO: perform_create, no perform_request
        serializer.save(usuario=self.request.user)
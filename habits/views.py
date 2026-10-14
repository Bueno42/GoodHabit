import boto3
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from botocore.exceptions import ClientError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from .models import Evidencia
from .serializers import EvidenciaSerializer, PresignedURLSerializer
from .services import generar_presigned_url_s3

from .models import Habit, HabitLog, HabitPadrino
from .serializers import HabitSerializer, HabitLogSerializer, HabitPadrinoSerializer

class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='invitar-padrino')
    def invitar_padrino(self, request, pk=None):
        habito = self.get_object()  # 404 si el hábito no pertenece al usuario autenticado

        padrino_id = request.data.get('padrino_id')
        if not padrino_id:
            return Response({'error': 'Debe proporcionar padrino_id.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            usuario_padrino = User.objects.get(pk=padrino_id)
        except User.DoesNotExist:
            return Response({'error': 'El usuario especificado no existe.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            asignacion = HabitPadrino.objects.create(
                habit=habito,
                padrino=usuario_padrino
            )
        except ValidationError as e:
            return Response({'error': e.messages}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            return Response({'error': 'Este usuario ya fue asignado a este hábito.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = HabitPadrinoSerializer(asignacion)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # En HabitViewSet actualizar check_in:
    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        habit = self.get_object()
        today = timezone.localdate()
        
        actual_value = request.data.get('actual_value', habit.target_value)
        notes = request.data.get('notes', '')
        s3_url = request.data.get('s3_file_url', None)

        # Regla de Negocio: Con padrinos va a revisión; sin padrinos se auto-aprueba
        estado_inicial = (
            HabitLog.Estado.EN_REVISION 
            if habit.tiene_padrinos_activos() 
            else HabitLog.Estado.APROBADO
        )

        log, created = HabitLog.objects.update_or_create(
            habit=habit,
            date=today,
            defaults={
                'estado': estado_inicial,
                'actual_value': actual_value,
                'notes': notes,
                'fecha_revision': timezone.now() if estado_inicial == HabitLog.Estado.APROBADO else None
            }
        )

        # Si mandó evidencia S3, la persistimos vinculada al log
        if s3_url:
            Evidencia.objects.update_or_create(
                habit_log=log,
                defaults={
                    'usuario': request.user,
                    's3_file_url': s3_url,
                    'descripcion': notes
                }
            )

        serializer = HabitLogSerializer(log)
        return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)


class HabitPadrinoViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = HabitPadrinoSerializer

    def get_queryset(self):
        # Aislamiento: solo las invitaciones dirigidas al usuario en sesión
        return HabitPadrino.objects.filter(padrino=self.request.user)

    @action(detail=False, methods=['get'], url_path='mis-solicitudes')
    def mis_solicitudes(self, request):
        solicitudes = self.get_queryset().filter(
            estado_invitacion=HabitPadrino.EstadoInvitacion.PENDIENTE
        )
        data = [
            {
                'id': s.id,
                'habito_id': s.habit.id,
                'habito_nombre': s.habit.name,
                'creador': s.habit.user.username if s.habit.user else 'Sistema',
                'fecha_asignacion': s.fecha_asignacion
            }
            for s in solicitudes
        ]
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='responder')
    def responder(self, request, pk=None):
        asignacion = self.get_object()  # Valida automáticamente pertenencia por get_queryset

        nuevo_estado = request.data.get('estado')
        if nuevo_estado not in [HabitPadrino.EstadoInvitacion.ACEPTADO, HabitPadrino.EstadoInvitacion.RECHAZADO]:
            return Response(
                {'error': 'Estado no válido. Use ACEPTADO o RECHAZADO.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if asignacion.estado_invitacion != HabitPadrino.EstadoInvitacion.PENDIENTE:
            return Response(
                {'error': 'Esta invitación ya fue respondida.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        asignacion.estado_invitacion = nuevo_estado
        asignacion.save()

        return Response(
            {'mensaje': f'Invitación respondida exitosamente como {nuevo_estado}.'},
            status=status.HTTP_200_OK
        )


class HabitLogViewSet(viewsets.ModelViewSet):
    serializer_class = HabitLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Un usuario ve sus propios logs
        return HabitLog.objects.filter(habit__user=self.request.user)

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
        # Obtenemos el log sin filtrar por habit__user=request.user
        try:
            log = HabitLog.objects.get(pk=pk)
        except HabitLog.DoesNotExist:
            return Response({'error': 'Registro no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        # Validación de autorización: ¿Es realmente padrino activo de este hábito?
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

        # Regla: 1 de 2 aprueba y consolida
        log.estado = nuevo_estado
        log.revisado_por = request.user
        log.fecha_revision = timezone.now()
        log.motivo_rechazo = motivo if nuevo_estado == HabitLog.Estado.RECHAZADO else None
        log.save()

        return Response(HabitLogSerializer(log).data, status=status.HTTP_200_OK)

class PresignedURLView(APIView):
    permission_classes = [permissions.IsAuthenticated]

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

class EvidenciaViewSet(viewsets.ModelViewSet):
    serializer_class = EvidenciaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Evidencia.objects.filter(usuario=self.request.user)

    def perform_create(self, serializer):  # CORREGIDO: perform_create, no perform_request
        serializer.save(usuario=self.request.user)
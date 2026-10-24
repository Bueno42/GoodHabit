from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HabitViewSet, HabitLogViewSet, HabitPadrinoViewSet, EvidenciaViewSet, PresignedURLView, UserViewSet

router = DefaultRouter()
router.register(r'habits', HabitViewSet, basename='habit')
router.register(r'logs', HabitLogViewSet, basename='log')
router.register(r'padrinazgos', HabitPadrinoViewSet, basename='padrinazgo')
router.register(r'evidencias', EvidenciaViewSet, basename='evidencia')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('s3/presigned-url/', PresignedURLView.as_view(), name='s3-presigned-url'),
]
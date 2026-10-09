from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HabitViewSet, HabitLogViewSet, HabitPadrinoViewSet

router = DefaultRouter()
router.register(r'habits', HabitViewSet, basename='habit')
router.register(r'logs', HabitLogViewSet, basename='log')
router.register(r'padrinazgos', HabitPadrinoViewSet, basename='padrinazgo')

urlpatterns = [
    path('', include(router.urls)),
]
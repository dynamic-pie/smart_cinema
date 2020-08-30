from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from core.views import GetMovie, UserCreate, LoginView, GetRecommendation


urlpatterns = [
    path('api-auth/', include('rest_framework.urls')),
    path('admin/', admin.site.urls),
    path('register/', UserCreate.as_view(), name='account-create'),
    path('login/', LoginView.as_view(), name='account-login'),
    path('sample/', GetRecommendation.as_view(), name='account-auth'),
    path('movie_info/<int:pk>', GetMovie.as_view(), name='movie-info'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

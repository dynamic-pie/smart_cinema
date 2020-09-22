from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from core.views import GetMovie, UserCreate, LoginView, GetRecommendation, GetMovies, SetMark, GetSessions, BuyTicket, GetSessionInfo


urlpatterns = [
    path('api-auth/', include('rest_framework.urls')),
    path('admin/', admin.site.urls),
    path('register/', UserCreate.as_view(), name='account-create'),
    path('login/', LoginView.as_view(), name='account-login'),
    path('recommendation/', GetRecommendation.as_view(), name='account-auth'),
    path('movies/', GetMovies.as_view(), name='account-auth'),
    path('buy_ticket/', BuyTicket.as_view(), name='account-auth'),
    path('get_session_info/', GetSessionInfo.as_view(), name='account-auth'),
    path('get_sessions/', GetSessions.as_view(), name='get-sessions'),
    path('set_mark/', SetMark.as_view(), name='set-mark'),
    path('movie_info/<int:pk>', GetMovie.as_view(), name='movie-info')

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

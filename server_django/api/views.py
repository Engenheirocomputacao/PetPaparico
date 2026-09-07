from django.shortcuts import get_object_or_404, render
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
import rest_framework # pyrefly: ignore [missing-import]
from rest_framework import status, viewsets # pyrefly: ignore [missing-import]
from rest_framework.decorators import action, api_view, permission_classes # pyrefly: ignore [missing-import]
from rest_framework.permissions import AllowAny, IsAuthenticated # pyrefly: ignore [missing-import]
from rest_framework.response import Response # pyrefly: ignore [missing-import]
from rest_framework.views import APIView # pyrefly: ignore [missing-import]
from .models import Pet, FeedingHistory, CustomUser, FeedingSchedule, CameraFeed, MediaCapture, DeviceStatus, Notification, NotificationSettings
from .serializers import UserSerializer, PetSerializer, FeedingScheduleSerializer, FeedingHistorySerializer, CameraFeedSerializer, MediaCaptureSerializer, DeviceStatusSerializer, NotificationSerializer, NotificationSettingsSerializer
from .notification_utils import create_notification, notify_feeding_completed, notify_low_food, notify_device_offline, check_and_notify_low_food
import json


def login_view(request):
    """
    View de login usando Django puro para garantir que cookies funcionem
    POST /api/login/
    """
    # Permitir apenas POST
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        print(f"DEBUG LOGIN: Tentando login com username='{username}'")
        
        if not username or not password:
            return JsonResponse(
                {'error': 'Username e password são obrigatórios'},
                status=400
            )
        
        # Verificar se usuário existe
        from api.models import CustomUser
        try:
            user_obj = CustomUser.objects.get(username=username)
            print(f"DEBUG LOGIN: Usuário encontrado - is_active={user_obj.is_active}, has_password={bool(user_obj.password)}")
        except CustomUser.DoesNotExist:
            print(f"DEBUG LOGIN: Usuário '{username}' NÃO existe no banco")
        
        user = authenticate(request, username=username, password=password)
        print(f"DEBUG LOGIN: authenticate() retornou: {user}")
        
        if user is not None:
            django_login(request, user)
            
            # Debug: verificar se a sessão foi criada
            print(f"DEBUG LOGIN: Session key = {request.session.session_key}")
            print(f"DEBUG LOGIN: User authenticated = {request.user.is_authenticated}")
            
            # Serializar dados do usuário
            from .serializers import UserSerializer
            serializer = UserSerializer(user, context={'request': request})
            
            response = JsonResponse({
                'success': True,
                'user': serializer.data
            })
            
            # Forçar cookie na resposta
            response.set_cookie(
                'sessionid',
                request.session.session_key,
                httponly=True,
                samesite='Lax',
                path='/',
                max_age=1209600  # 2 semanas
            )
            
            print(f"DEBUG LOGIN: Cookie setado na resposta")
            
            return response
        else:
            print(f"DEBUG LOGIN: Autenticação falhou para '{username}'")
            return JsonResponse(
                {'error': 'Credenciais inválidas'},
                status=401
            )
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


def register_view(request):
    """
    View de cadastro de novo usuário
    POST /api/register/
    Body: { "username": "...", "password": "...", "email": "..." }
    """
    # Permitir apenas POST
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        print(f"DEBUG REGISTER: Tentando criar usuário username='{username}', email='{email}'")
        
        if not username or not password:
            print(f"DEBUG REGISTER: Campos obrigatórios faltando")
            return JsonResponse(
                {'error': 'Username e password são obrigatórios'},
                status=400
            )
        
        # Verificar se usuário já existe
        from api.models import CustomUser
        if CustomUser.objects.filter(username=username).exists():
            print(f"DEBUG REGISTER: Username '{username}' já existe")
            return JsonResponse(
                {'error': 'Username já está em uso'},
                status=400
            )
        
        # Criar novo usuário
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=True
        )
        
        print(f"DEBUG REGISTER: Usuário '{username}' criado com sucesso (id={user.id})")
        
        # Fazer login automático após cadastro
        django_login(request, user)
        
        # Serializar dados do usuário
        from .serializers import UserSerializer
        serializer = UserSerializer(user, context={'request': request})
        
        response = JsonResponse({
            'success': True,
            'user': serializer.data,
            'message': 'Usuário criado com sucesso!'
        })
        
        # Set session cookie
        response.set_cookie(
            'sessionid',
            request.session.session_key,
            httponly=True,
            samesite='Lax',
            path='/',
            max_age=1209600
        )
        
        print(f"DEBUG REGISTER: Login automático realizado, cookie setado")
        
        return response
        
    except json.JSONDecodeError:
        print(f"DEBUG REGISTER: JSON inválido")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"DEBUG REGISTER: Erro ao criar usuário: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse(
            {'error': f'Erro ao criar usuário: {str(e)}'},
            status=500
        )


@csrf_exempt
@require_POST
def logout_view(request):
    """
    View de logout usando Django puro
    POST /api/logout/
    """
    django_logout(request)
    return JsonResponse({'success': True, 'message': 'Logout realizado com sucesso'})


# --- ViewSets API ---

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    # Usar autenticação por sessão do Django
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [AllowAny]  # Manter AllowAny para permitir login

    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def me(self, request):
        # Debug: verificar cookies e autenticação
        print(f"DEBUG ME: Cookies recebidos = {request.COOKIES.keys()}")
        print(f"DEBUG ME: Session key nos cookies = {request.COOKIES.get('sessionid', 'NÃO ENCONTRADO')}")
        print(f"DEBUG ME: User authenticated = {request.user.is_authenticated}")
        print(f"DEBUG ME: User = {request.user}")
        
        # Exigir autenticação real - sem mock
        if not request.user or not request.user.is_authenticated:
            return Response({'detail': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        
        if request.method == 'GET':
            serializer = self.get_serializer(user)
            return Response(serializer.data)
        
        if request.method == 'PATCH':
            # Support both JSON and FormData (for photo upload)
            serializer = self.get_serializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                # Manually handle first_name/last_name if name is sent (optional, based on frontend)
                if 'name' in request.data and not ('first_name' in request.data):
                    name_parts = request.data['name'].split(' ', 1)
                    user.first_name = name_parts[0]
                    if len(name_parts) > 1:
                        user.last_name = name_parts[1]
                
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PetViewSet(viewsets.ModelViewSet):
    serializer_class = PetSerializer
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]
    
    # Queryset vazio como fallback - será sobrescrito por get_queryset
    queryset = Pet.objects.none()

    def get_queryset(self):
        # Retornar apenas pets do usuário logado
        if self.request.user and self.request.user.is_authenticated:
            return Pet.objects.filter(user=self.request.user)
        return Pet.objects.none()

    def perform_create(self, serializer):
        # Associar pet ao usuário logado
        serializer.save(user=self.request.user)

class FeedingScheduleViewSet(viewsets.ModelViewSet):
    queryset = FeedingSchedule.objects.none()
    serializer_class = FeedingScheduleSerializer
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = FeedingSchedule.objects.none()
        if self.request.user and self.request.user.is_authenticated:
            queryset = FeedingSchedule.objects.filter(pet__user=self.request.user)
            pet_id = self.request.query_params.get('pet')
            if pet_id:
                queryset = queryset.filter(pet_id=pet_id)
        return queryset

class FeedingHistoryViewSet(viewsets.ModelViewSet):
    queryset = FeedingHistory.objects.none()
    serializer_class = FeedingHistorySerializer
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = FeedingHistory.objects.none()
        if self.request.user and self.request.user.is_authenticated:
            queryset = FeedingHistory.objects.filter(pet__user=self.request.user).order_by('-timestamp')
            pet_id = self.request.query_params.get('pet')
            if pet_id:
                queryset = queryset.filter(pet_id=pet_id)
        return queryset

class CameraFeedViewSet(viewsets.ModelViewSet):
    queryset = CameraFeed.objects.none()
    serializer_class = CameraFeedSerializer
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = CameraFeed.objects.none()
        if self.request.user and self.request.user.is_authenticated:
            queryset = CameraFeed.objects.filter(pet__user=self.request.user)
            pet_id = self.request.query_params.get('pet')
            if pet_id:
                queryset = queryset.filter(pet_id=pet_id)
        return queryset

class MediaCaptureViewSet(viewsets.ModelViewSet):
    queryset = MediaCapture.objects.none()
    serializer_class = MediaCaptureSerializer
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = MediaCapture.objects.none()
        if self.request.user and self.request.user.is_authenticated:
            queryset = MediaCapture.objects.filter(cameraFeed__pet__user=self.request.user)
        return queryset

class DeviceStatusViewSet(viewsets.ModelViewSet):
    queryset = DeviceStatus.objects.none()
    serializer_class = DeviceStatusSerializer
    authentication_classes = [rest_framework.authentication.SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = DeviceStatus.objects.none()
        if self.request.user and self.request.user.is_authenticated:
            queryset = DeviceStatus.objects.filter(user=self.request.user)
        return queryset

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]  # Exigir autenticação
    authentication_classes = [rest_framework.authentication.SessionAuthentication]

    def get_queryset(self):
        # Retorna APENAS notificações do usuário autenticado
        user = self.request.user
        return Notification.objects.filter(user=user).order_by('-sentAt')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Marcar notificação como lida
        POST /api/notifications/<id>/mark_read/
        """
        try:
            notification = self.get_object()
            notification.isRead = True
            notification.readAt = timezone.now()
            notification.save()
            
            return Response({
                'success': True,
                'message': 'Notificação marcada como lida'
            })
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notificação não encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_notification_view(request):
    """
    Endpoint para criar uma notificação manualmente
    
    POST /api/notifications/send/
    {
        "user_id": 1,
        "type": "feeding_completed|low_food|device_offline|general",
        "title": "Título da notificação",
        "message": "Mensagem da notificação",
        "send_email": true,
        "send_push": true
    }
    """
    user_id = request.data.get('user_id')
    notification_type = request.data.get('type', 'general')
    title = request.data.get('title', '')
    message = request.data.get('message', '')
    send_email = request.data.get('send_email', True)
    send_push = request.data.get('send_push', True)
    
    if not user_id:
        return Response(
            {'error': 'user_id é obrigatório'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'Usuário não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Validar tipo de notificação
    valid_types = ['feeding_completed', 'low_food', 'device_offline', 'general']
    if notification_type not in valid_types:
        return Response(
            {'error': f'Tipo de notificação inválido. Use: {valid_types}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        notification = create_notification(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            send_email=send_email,
            send_push=send_push
        )
        
        if notification is None:
            return Response(
                {'message': 'Notificação desabilitada nas configurações do usuário'},
                status=status.HTTP_200_OK
            )
        
        return Response({
            'success': True,
            'notification_id': notification.id,
            'type': notification.type,
            'title': notification.title,
            'message': notification.message,
            'sentAt': notification.sentAt
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Erro ao criar notificação: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def mark_notification_read_view(request, notification_id):
    """
    Marcar notificação como lida
    
    POST /api/notifications/<id>/mark-read/
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.isRead = True
        notification.readAt = timezone.now()
        notification.save()
        
        return Response({
            'success': True,
            'message': 'Notificação marcada como lida'
        })
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notificação não encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def test_low_food_notification(request):
    """
    Endpoint para testar notificação de ração baixa
    
    POST /api/notifications/test/low-food/
    {
        "user_id": 1,
        "food_level": 15
    }
    """
    user_id = request.data.get('user_id')
    food_level = request.data.get('food_level', 15)
    
    if not user_id:
        return Response(
            {'error': 'user_id é obrigatório'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return Response(
            {'error': 'Usuário não encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    notification = check_and_notify_low_food(user, food_level)
    
    if notification:
        return Response({
            'success': True,
            'message': f'Notificação de ração baixa enviada (nível: {food_level}%)',
            'notification_id': notification.id
        })
    else:
        return Response({
            'success': False,
            'message': 'Notificação de ração baixa está desabilitada nas configurações'
        })

class NotificationSettingsViewSet(viewsets.ModelViewSet):
    queryset = NotificationSettings.objects.all()
    serializer_class = NotificationSettingsSerializer
    permission_classes = [IsAuthenticated]  # Exigir autenticação
    authentication_classes = [rest_framework.authentication.SessionAuthentication]

    def get_queryset(self):
        # Retorna configurações do usuário autenticado
        user = self.request.user
        if user.is_authenticated:
            return NotificationSettings.objects.filter(user=user)
        return NotificationSettings.objects.none()
    
    def perform_create(self, serializer):
        # Associar configurações ao usuário autenticado
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            raise Exception("Usuário deve estar autenticado")
    
    @csrf_exempt
    def create(self, request, *args, **kwargs):
        # Se já existe configurações para o usuário, fazer update
        if request.user.is_authenticated:
            settings_obj, created = NotificationSettings.objects.get_or_create(
                user=request.user
            )
            serializer = self.get_serializer(settings_obj, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(
            {'error': 'Usuário deve estar autenticado'},
            status=status.HTTP_401_UNAUTHORIZED
        )


def esp32_simulator_view(request):
    """
    View para página de simulação do ESP32
    GET /api/device/simulator/
    """
    # Ocultar a navegação lateral nesta página para melhorar a visualização
    return render(request, 'api/esp32_simulator.html', { 'show_nav': False })


def device_page_view(request):
    """
    View para página principal do Device
    GET /api/device/
    """
    return render(request, 'api/device_page.html')


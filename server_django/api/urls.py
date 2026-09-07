from django.urls import path, include
# pyrefly: ignore [missing-import]
from rest_framework.routers import DefaultRouter # pyrefly: ignore [missing-import]
from . import views
from . import servo_views

router = DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'pets', views.PetViewSet)
router.register(r'schedules', views.FeedingScheduleViewSet, basename='feedingschedule')
router.register(r'history', views.FeedingHistoryViewSet, basename='feedinghistory')
router.register(r'cameras', views.CameraFeedViewSet, basename='camerafeed')
router.register(r'captures', views.MediaCaptureViewSet)
router.register(r'status', views.DeviceStatusViewSet)
router.register(r'notifications', views.NotificationViewSet)
router.register(r'settings', views.NotificationSettingsViewSet)

urlpatterns = [
    # Device Page
    path('device/', views.device_page_view, name='device_page'),

    # ESP32 IoT Endpoints
    path('feed/', servo_views.trigger_feeding, name='trigger_feeding'),
    path('device/status/', servo_views.get_device_status, name='device_status'),
    path('device/test/', servo_views.test_connection, name='test_connection'),
    path('servo/calibrate/', servo_views.calibrate_servo, name='calibrate_servo'),
    path('device/simulator/settings/', servo_views.update_simulator_settings, name='update_simulator_settings'),
    path('device/refill/', servo_views.refill_food_container, name='refill_food_container'),
    path('device/simulator/', views.esp32_simulator_view, name='esp32_simulator'),

    # Notification Endpoints
    path('notifications/send/', views.create_notification_view, name='create_notification'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('notifications/test/low-food/', views.test_low_food_notification, name='test_low_food_notification'),

    # Auth Endpoints
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # API Router
    path('', include(router.urls)),
]

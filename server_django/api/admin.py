from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Pet, FeedingSchedule, FeedingHistory, CameraFeed, MediaCapture, DeviceStatus, Notification, NotificationSettings

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'role')
    search_fields = ('username', 'email')
    ordering = ('username',)
    
    # Campos exibidos ao criar novo usuário
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'role'),
        }),
    )
    
    # Campos exibidos ao editar usuário existente
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'bio', 'photo', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'createdAt', 'updatedAt')}),
    )
    
    readonly_fields = ('createdAt', 'updatedAt', 'last_login')

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'breed', 'defaultQuantity', 'user')
    search_fields = ('name', 'species')
    fieldsets = (
        (None, {'fields': ('user', 'name', 'species', 'breed')}),
        ('Informações', {'fields': ('age', 'weight', 'defaultQuantity', 'photo', 'photoUrl', 'photoKey', 'notes')}),
    )

@admin.register(FeedingSchedule)
class FeedingScheduleAdmin(admin.ModelAdmin):
    list_display = ('pet', 'time', 'quantity', 'frequency', 'isActive')

@admin.register(FeedingHistory)
class FeedingHistoryAdmin(admin.ModelAdmin):
    list_display = ('pet', 'quantity', 'feedingType', 'timestamp', 'success', 'notes')
    list_filter = ('feedingType', 'success', 'timestamp')
    search_fields = ('pet__name', 'notes')
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp',)

@admin.register(CameraFeed)
class CameraFeedAdmin(admin.ModelAdmin):
    list_display = ('name', 'pet', 'isActive')

@admin.register(MediaCapture)
class MediaCaptureAdmin(admin.ModelAdmin):
    list_display = ('cameraFeed', 'mediaType', 'timestamp')

@admin.register(DeviceStatus)
class DeviceStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'isOnline', 'batteryLevel', 'foodLevel', 'lastSeen')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'type', 'isRead', 'sentAt')

@admin.register(NotificationSettings)
class NotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'emailFeedingCompleted', 'pushFeedingCompleted')

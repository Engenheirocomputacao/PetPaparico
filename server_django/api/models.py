from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from urllib.parse import urlparse

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('tutor', 'Tutor'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='tutor')
    photo = models.ImageField(upload_to='users/', null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    cpf = models.CharField(max_length=14, null=True, blank=True, help_text='CPF no formato XXX.XXX.XXX-XX')
    telefone = models.CharField(max_length=20, null=True, blank=True, help_text='Telefone com DDD')
    profissao = models.CharField(max_length=100, null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=2, null=True, blank=True, help_text='UF - Ex: SP, RJ, MG')
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

class Pet(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='pets')
    name = models.CharField(max_length=255)
    species = models.CharField(max_length=100, null=True, blank=True)
    breed = models.CharField(max_length=100, null=True, blank=True)
    photo = models.ImageField(upload_to='pets/', null=True, blank=True)
    photoUrl = models.TextField(null=True, blank=True) # Mantido para compatibilidade se necessário
    photoKey = models.CharField(max_length=255, null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    dispenser_channel = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, f"Reservatório {i}") for i in range(1, 6)],
        help_text='Canal do servo/dispensador (1-5) associado a este pet',
    )
    defaultQuantity = models.IntegerField(default=50, help_text='Quantidade padrão em gramas')
    notes = models.TextField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'dispenser_channel'],
                condition=~models.Q(dispenser_channel=None),
                name='unique_dispenser_channel_per_user'
            )
        ]

class FeedingSchedule(models.Model):
    FREQ_CHOICES = [
        ('daily', 'Daily'),
        ('weekdays', 'Weekdays'),
        ('weekends', 'Weekends'),
        ('custom', 'Custom'),
    ]
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='schedules')
    time = models.CharField(max_length=5)
    quantity = models.IntegerField()
    frequency = models.CharField(max_length=20, choices=FREQ_CHOICES, default='daily')
    daysOfWeek = models.CharField(max_length=50, null=True, blank=True)
    isActive = models.BooleanField(default=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

class FeedingHistory(models.Model):
    TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('scheduled', 'Scheduled'),
    ]
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='feeding_history')
    quantity = models.IntegerField()
    feedingType = models.CharField(max_length=20, choices=TYPE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)

class CameraFeed(models.Model):
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='cameras')
    name = models.CharField(max_length=255)
    rtspUrl = models.TextField()
    isActive = models.BooleanField(default=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def clean(self):
        url = (self.rtspUrl or '').strip()
        if not url:
            raise ValidationError({'rtspUrl': 'A URL da câmera não pode ficar vazia.'})
        if 'youtube.com/watch?v=' in url or 'youtu.be/' in url or 'twitch.tv/' in url:
            return
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https', 'rtsp') or not parsed.netloc:
            raise ValidationError({'rtspUrl': 'URL da câmera inválida ou não suportada.'})

class MediaCapture(models.Model):
    TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]
    cameraFeed = models.ForeignKey(CameraFeed, on_delete=models.CASCADE, related_name='captures')
    mediaType = models.CharField(max_length=10, choices=TYPE_CHOICES)
    mediaUrl = models.TextField()
    mediaKey = models.CharField(max_length=255)
    duration = models.IntegerField(null=True, blank=True)
    fileSize = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    expiresAt = models.DateTimeField(null=True, blank=True)

    def clean(self):
        url = (self.mediaUrl or '').strip()
        if not url:
            raise ValidationError({'mediaUrl': 'A URL da mídia não pode ficar vazia.'})

class DeviceStatus(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='devices')
    channel = models.IntegerField(
        null=True,
        blank=True,
        choices=[(i, f"Dispensador {i+1}") for i in range(5)],
        help_text='Canal/dispositivo específico (0-4)'
    )
    isOnline = models.BooleanField(default=True)
    batteryLevel = models.IntegerField(null=True, blank=True)
    foodLevel = models.IntegerField(null=True, blank=True)
    lastSeen = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'channel'],
                name='unique_device_channel_per_user'
            )
        ]

class Notification(models.Model):
    TYPE_CHOICES = [
        ('feeding_completed', 'Feeding Completed'),
        ('low_food', 'Low Food'),
        ('device_offline', 'Device Offline'),
        ('dispenser_cleaning', 'Dispenser Cleaning'),
        ('general', 'General'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    isRead = models.BooleanField(default=False)
    sentAt = models.DateTimeField(auto_now_add=True)
    readAt = models.DateTimeField(null=True, blank=True)

class NotificationSettings(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='notification_settings')
    emailFeedingCompleted = models.BooleanField(default=True)
    emailLowFood = models.BooleanField(default=True)
    emailDeviceOffline = models.BooleanField(default=True)
    emailDispenserCleaning = models.BooleanField(default=True)
    pushFeedingCompleted = models.BooleanField(default=True)
    pushLowFood = models.BooleanField(default=True)
    pushDeviceOffline = models.BooleanField(default=True)
    pushDispenserCleaning = models.BooleanField(default=True)
    lowFoodThreshold = models.IntegerField(default=20)
    dispenserCleaningReminderDays = models.IntegerField(default=3)
    lastDispenserCleaningReminderAt = models.DateTimeField(null=True, blank=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

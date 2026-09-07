from rest_framework import serializers # pyrefly: ignore [missing-import]
from .web_helpers import clean_camera_url
from .models import CustomUser, Pet, FeedingSchedule, FeedingHistory, CameraFeed, MediaCapture, DeviceStatus, Notification, NotificationSettings

class UserSerializer(serializers.ModelSerializer):
    photoUrl = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'photo', 'photoUrl', 'bio', 'first_name', 'last_name', 'name', 'createdAt']
        read_only_fields = ['id', 'createdAt']

    def get_photoUrl(self, obj):
        if obj.photo:
            try:
                request = self.context.get('request')
                if request is not None:
                    return request.build_absolute_uri(obj.photo.url)
                return obj.photo.url
            except Exception:
                return None
        return None

    def get_name(self, obj):
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.username

class PetSerializer(serializers.ModelSerializer):
    photoUrl = serializers.SerializerMethodField()

    class Meta:
        model = Pet
        fields = '__all__'
        read_only_fields = ['user', 'createdAt', 'updatedAt']

    def get_photoUrl(self, obj):
        if obj.photo:
            try:
                # Retorna a URL completa para o frontend
                request = self.context.get('request')
                if request is not None:
                    return request.build_absolute_uri(obj.photo.url)
                return obj.photo.url
            except Exception:
                return None
        return obj.photoUrl

class FeedingScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedingSchedule
        fields = '__all__'
        read_only_fields = ['createdAt', 'updatedAt']

class FeedingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedingHistory
        fields = '__all__'

class CameraFeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CameraFeed
        fields = '__all__'

    def validate_rtspUrl(self, value):
        cleaned = clean_camera_url(value)
        if not cleaned:
            raise serializers.ValidationError('URL da câmera inválida ou não suportada.')
        return cleaned

class MediaCaptureSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaCapture
        fields = '__all__'

    def validate_mediaUrl(self, value):
        if not value or not str(value).strip():
            raise serializers.ValidationError('A URL da mídia não pode ficar vazia.')
        return str(value).strip()

class DeviceStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceStatus
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class NotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSettings
        fields = '__all__'

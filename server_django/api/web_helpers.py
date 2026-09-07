"""Funções auxiliares para views HTML."""
from django.utils import timezone
from urllib.parse import urlparse

from .iot_client import esp32_client
from .models import CameraFeed, DeviceStatus, FeedingHistory, FeedingSchedule, MediaCapture, Pet


def user_display_name(user):
    if not user or not user.is_authenticated:
        return ""
    if user.first_name or user.last_name:
        return f"{user.first_name} {user.last_name}".strip()
    return user.username


def user_photo_url(user, request=None):
    """URL da foto de perfil (caminho absoluto a partir da raiz do site)."""
    if not user or not user.is_authenticated:
        return None
    try:
        if not user.photo or not user.photo.name:
            return None
        url = user.photo.url
        if request is not None:
            return request.build_absolute_uri(url)
        return url
    except (ValueError, OSError):
        return None


def user_initial(user):
    name = user_display_name(user)
    return name[0].upper() if name else "?"


def nav_context(request):
    path = request.path
    user = request.user
    return {
        "user_photo_url": user_photo_url(user, request),
        "user_initial": user_initial(user),
        "nav_items": [
            {"url": "/", "label": "Minha Casa", "icon": "🏠", "active": path == "/"},
            {"url": "/pets/", "label": "Meus Pets", "icon": "🐾", "active": path.startswith("/pets")},
            {"url": "/feeding/", "label": "Alimentação", "icon": "🍽️", "active": path.startswith("/feeding")},
            {"url": "/history/", "label": "Histórico", "icon": "🕐", "active": path.startswith("/history")},
            {"url": "/cameras/", "label": "Câmeras", "icon": "📷", "active": path.startswith("/cameras")},
            {"url": "/device/", "label": "Dispositivo", "icon": "⚙️", "active": path.startswith("/device")},
            {"url": "/notifications/", "label": "Notificações", "icon": "🔔", "active": path.startswith("/notifications")},
        ],
        "display_name": user_display_name(request.user),
    }


def get_user_pets(user):
    return Pet.objects.filter(user=user).order_by("name")


def get_selected_pet(user, pet_id):
    if not pet_id:
        return None
    try:
        return Pet.objects.get(pk=int(pet_id), user=user)
    except (Pet.DoesNotExist, ValueError, TypeError):
        return None


def sync_device_status(user, channel: int = None):
    """Atualiza DeviceStatus no banco a partir do ESP32 para um canal específico ou todos."""
    if channel is not None:
        # Sincronizar canal específico
        esp32_status = esp32_client.get_status(channel)
        if esp32_status:
            device = DeviceStatus.objects.filter(user=user, channel=channel).order_by('-updatedAt', '-lastSeen', '-id').first()
            if device is None:
                device = DeviceStatus.objects.create(
                    user=user,
                    channel=channel,
                    isOnline=esp32_status.get("online", False),
                    foodLevel=esp32_status.get("food_level"),
                    batteryLevel=esp32_status.get("battery_level"),
                    lastSeen=timezone.now(),
                )
            else:
                device.isOnline = esp32_status.get("online", False)
                device.foodLevel = esp32_status.get("food_level")
                device.batteryLevel = esp32_status.get("battery_level")
                device.lastSeen = timezone.now()
                device.save()
            return device, esp32_status
        # Se não conseguir status, marca como offline
        device = DeviceStatus.objects.filter(user=user, channel=channel).order_by('-updatedAt', '-lastSeen', '-id').first()
        if device is None:
            device = DeviceStatus.objects.create(
                user=user,
                channel=channel,
                isOnline=False,
                lastSeen=timezone.now(),
            )
        else:
            device.isOnline = False
            device.lastSeen = timezone.now()
            device.save()
        return device, None
    else:
        # Sincronizar todos os canais (0-4)
        all_status = esp32_client.get_all_channels_status()
        devices = []
        for ch in range(5):
            esp32_status = all_status.get(ch)
            if esp32_status:
                device = DeviceStatus.objects.filter(user=user, channel=ch).order_by('-updatedAt', '-lastSeen', '-id').first()
                if device is None:
                    device = DeviceStatus.objects.create(
                        user=user,
                        channel=ch,
                        isOnline=esp32_status.get("online", False),
                        foodLevel=esp32_status.get("food_level"),
                        batteryLevel=esp32_status.get("battery_level"),
                        lastSeen=timezone.now(),
                    )
                else:
                    device.isOnline = esp32_status.get("online", False)
                    device.foodLevel = esp32_status.get("food_level")
                    device.batteryLevel = esp32_status.get("battery_level")
                    device.lastSeen = timezone.now()
                    device.save()
                devices.append(device)
            else:
                # Marcar como offline
                device = DeviceStatus.objects.filter(user=user, channel=ch).order_by('-updatedAt', '-lastSeen', '-id').first()
                if device is None:
                    device = DeviceStatus.objects.create(
                        user=user,
                        channel=ch,
                        isOnline=False,
                        lastSeen=timezone.now(),
                    )
                else:
                    device.isOnline = False
                    device.lastSeen = timezone.now()
                    device.save()
                devices.append(device)
        return devices, all_status


def feeding_stats(pet, filter_period='all'):
    """
    Retorna estatísticas de alimentação com filtros
    filter_period: 'day', 'week', 'month', 'year', 'all'
    """
    from django.utils import timezone
    from datetime import timedelta
    
    now = timezone.now()
    
    # Filtrar por período
    if filter_period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filter_period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif filter_period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # 'all'
        start_date = None
    
    # Queryset base
    history_qs = FeedingHistory.objects.filter(pet=pet)
    if start_date:
        history_qs = history_qs.filter(timestamp__gte=start_date)
    
    history_qs = history_qs.order_by("-timestamp")
    
    # Estatísticas do período filtrado
    filtered_count = history_qs.count()
    filtered_total = sum(h.quantity for h in history_qs)
    
    # Alimentações por hora do dia (para gráfico)
    feedings_by_hour = {}
    for h in history_qs:
        hour = h.timestamp.hour
        feedings_by_hour[hour] = feedings_by_hour.get(hour, 0) + h.quantity
    
    # Alimentações por dia da semana
    days_pt = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
    feedings_by_day = {day: 0 for day in days_pt}
    for h in history_qs:
        day_idx = h.timestamp.weekday()
        feedings_by_day[days_pt[day_idx]] = feedings_by_day.get(days_pt[day_idx], 0) + h.quantity
    
    # Média por alimentação
    filtered_avg = round(filtered_total / filtered_count) if filtered_count > 0 else 0
    
    # Estatísticas gerais (sempre mostra tudo)
    all_history = FeedingHistory.objects.filter(pet=pet)
    last_feeding = all_history.order_by("-timestamp").first()
    total_all_time = sum(h.quantity for h in all_history)
    
    # Próximos agendamentos
    schedules = FeedingSchedule.objects.filter(pet=pet, isActive=True).order_by("time")
    next_schedule = schedules.first()
    
    return {
        "history": history_qs[:50],  # Últimas 50 do período
        "last_feeding": last_feeding,
        "total_kg_period": filtered_total / 1000,
        "count_period": filtered_count,
        "avg_period": filtered_avg,
        "total_kg_all": total_all_time / 1000,
        "count_all": all_history.count(),
        "schedules": schedules,
        "next_schedule_time": next_schedule.time if next_schedule else "---",
        "feedings_by_hour": feedings_by_hour,
        "feedings_by_day": feedings_by_day,
    }


def history_stats(history_qs):
    today = timezone.localdate()
    today_rows = [h for h in history_qs if h.timestamp.date() == today]
    total_today = sum(h.quantity for h in today_rows)
    avg = 0
    if history_qs:
        avg = round(sum(h.quantity for h in history_qs) / len(history_qs))
    return {
        "today_count": len(today_rows),
        "total_today": total_today,
        "average": avg,
        "total_count": len(history_qs),
    }


def _is_supported_camera_url(url: str) -> bool:
    if not url:
        return False
    clean = url.strip()
    if not clean:
        return False
    if "youtube.com/watch?v=" in clean or "youtu.be/" in clean or "twitch.tv/" in clean:
        return True
    parsed = urlparse(clean)
    if parsed.scheme in ("http", "https", "rtsp") and parsed.netloc:
        return True
    return False


def clean_camera_url(url: str) -> str:
    clean = url.strip()
    if "youtube.com/watch?v=" in clean:
        video_id = clean.split("v=")[1].split("&")[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if "youtu.be/" in clean:
        video_id = clean.split("youtu.be/")[1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"
    if "twitch.tv/" in clean and "player.twitch.tv" not in clean:
        channel = clean.split("twitch.tv/")[1].split("/")[0].split("?")[0]
        return f"https://player.twitch.tv/?channel={channel}&parent=localhost&autoplay=true&muted=true"
    return clean if _is_supported_camera_url(clean) else ""


def embed_camera_url(url: str) -> str:
    """URL para exibir no iframe/img."""
    clean = clean_camera_url(url)
    if not clean:
        return ""
    if clean.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return clean
    if "youtube.com/embed" in clean or "player.twitch.tv" in clean:
        return clean
    if any(x in clean.lower() for x in ("mjpg", "mjpeg", "stream", "snapshot")):
        return clean
    return clean

"""
Utilitário para envio de notificações
Centraliza a lógica de criação e envio de notificações
"""
from datetime import timedelta
from typing import Optional
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification, NotificationSettings, CustomUser, Pet


def create_notification(
    user: CustomUser,
    notification_type: str,
    title: str,
    message: str,
    send_email: bool = True,
    send_push: bool = True
) -> Notification:
    """
    Cria uma notificação para o usuário
    
    Args:
        user: Usuário que receberá a notificação
        notification_type: Tipo da notificação (feeding_completed, low_food, device_offline, general)
        title: Título da notificação
        message: Mensagem da notificação
        send_email: Se deve enviar por e-mail
        send_push: Se deve enviar por push
        
    Returns:
        Notification criada
    """
    # Verificar configurações do usuário
    email_settings = None
    try:
        email_settings = user.notification_settings
        should_notify = True
        
        # Verificar se notificações estão habilitadas para este tipo
        if notification_type == 'feeding_completed':
            should_notify = (email_settings.emailFeedingCompleted and send_email) or \
                           (email_settings.pushFeedingCompleted and send_push)
        elif notification_type == 'low_food':
            should_notify = (email_settings.emailLowFood and send_email) or \
                           (email_settings.pushLowFood and send_push)
        elif notification_type == 'device_offline':
            should_notify = (email_settings.emailDeviceOffline and send_email) or \
                           (email_settings.pushDeviceOffline and send_push)
        elif notification_type == 'dispenser_cleaning':
            should_notify = (email_settings.emailDispenserCleaning and send_email) or \
                           (email_settings.pushDispenserCleaning and send_push)

        if not should_notify:
            return None
            
    except NotificationSettings.DoesNotExist:
        # Se não houver configurações, cria notificação mesmo assim
        pass
    
    # Criar notificação no banco
    notification = Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        message=message,
        isRead=False,
        sentAt=timezone.now()
    )
    
    # Enviar email se habilitado
    if send_email and user.email:
        try:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost")
            send_mail(
                subject=title,
                message=message,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
            print(f"✅ Email enviado para {user.email}: {title}")
        except Exception as e:
            print(f"❌ Erro ao enviar email: {e}")
    
    # TODO: Implementar envio real de push notification
    # if send_push and user.push_token:
    #     send_push_notification(user.push_token, title, message)
    
    return notification


def notify_feeding_completed(user: CustomUser, pet_name: str, quantity: int) -> Optional[Notification]:
    """
    Notifica que uma alimentação foi completada com sucesso
    
    Args:
        user: Usuário dono do pet
        pet_name: Nome do pet que foi alimentado
        quantity: Quantidade de ração dispensada (gramas)
        
    Returns:
        Notification criada ou None
    """
    title = f"✅ Alimentação concluída - {pet_name}"
    message = f"{quantity}g de ração dispensado com sucesso para {pet_name}."
    
    return create_notification(
        user=user,
        notification_type='feeding_completed',
        title=title,
        message=message,
        send_email=True,
        send_push=True
    )


def notify_low_food(user: CustomUser, food_level: int, threshold: int = 20) -> Optional[Notification]:
    """
    Notifica que o nível de ração está baixo
    
    Args:
        user: Usuário dono do dispositivo
        food_level: Nível atual de ração (%)
        threshold: Threshold configurado para alerta
        
    Returns:
        Notification criada ou None
    """
    title = "⚠️ Ração baixa!"
    message = f"O nível de ração está em {food_level}%. Hora de reabastecer o alimentador!"
    
    return create_notification(
        user=user,
        notification_type='low_food',
        title=title,
        message=message,
        send_email=True,
        send_push=True
    )


def notify_device_offline(user: CustomUser, device_name: str = "ESP32 Pet Feeder") -> Optional[Notification]:
    """
    Notifica que o dispositivo está offline
    
    Args:
        user: Usuário dono do dispositivo
        device_name: Nome do dispositivo
        
    Returns:
        Notification criada ou None
    """
    title = "🔴 Dispositivo offline"
    message = f"{device_name} não está respondendo. Verifique a conexão e alimentação do dispositivo."
    
    return create_notification(
        user=user,
        notification_type='device_offline',
        title=title,
        message=message,
        send_email=True,
        send_push=True
    )


def notify_pet_did_not_eat(user: CustomUser, pet_name: str, pressure_percent: int, elapsed_minutes: int) -> Optional[Notification]:
    """Notifica quando a alimentação não foi consumida após 20 minutos."""
    title = "⚠️ Seu pet não se alimentou"
    message = (
        f"O sensor de pressão registrou {pressure_percent}% do peso programado para {pet_name} "
        f"após {elapsed_minutes} minutos da liberação da ração. Verifique se a refeição foi consumida."
    )
    return create_notification(
        user=user,
        notification_type='general',
        title=title,
        message=message,
        send_email=True,
        send_push=True,
    )


def notify_dispenser_full(user: CustomUser, pet_name: str, pressure_percent: int) -> Optional[Notification]:
    """Notifica quando o comedouro está quase cheio/lotado e a próxima porção deve ser bloqueada."""
    title = "⚠️ Comedouro cheio"
    message = (
        f"O sensor de pressão registrou {pressure_percent}% do peso programado para {pet_name}. "
        "A próxima porção foi bloqueada e o comedouro precisa ser verificado."
    )
    return create_notification(
        user=user,
        notification_type='general',
        title=title,
        message=message,
        send_email=True,
        send_push=True,
    )


def evaluate_feeding_pressure(
    pet: Pet,
    pressure_percent: int,
    elapsed_minutes: int = 0,
    send_notification: bool = True,
) -> dict:
    """
    Avalia a leitura do sensor de pressão do comedouro.

    Regras:
    - acima de 50% do peso programado e após 20 minutos => notifica "seu pet não se alimentou"
    - acima de 80% do peso programado => bloqueia a próxima porção e notifica "comedouro cheio"
    """
    pressure = max(0, min(100, int(pressure_percent or 0)))
    programmed_weight = int(pet.defaultQuantity or 50)

    decision = {
        "pressure_percent": pressure,
        "programmed_weight": programmed_weight,
        "skip_next_portion": pressure >= 80,
        "pet_did_not_eat": pressure > 50 and elapsed_minutes >= 20 and pressure < 80,
    }

    if send_notification:
        if decision["skip_next_portion"]:
            notify_dispenser_full(pet.user, pet.name, pressure)
        elif decision["pet_did_not_eat"]:
            notify_pet_did_not_eat(pet.user, pet.name, pressure, elapsed_minutes)

    return decision


def check_and_notify_low_food(user: CustomUser, food_level: int) -> Optional[Notification]:
    """
    Verifica se o nível de ração está abaixo do threshold e notifica se necessário
    
    Args:
        user: Usuário dono do dispositivo
        food_level: Nível atual de ração (%)
        
    Returns:
        Notification criada ou None
    """
    try:
        settings = user.notification_settings
        threshold = settings.lowFoodThreshold
    except NotificationSettings.DoesNotExist:
        threshold = 20  # Valor padrão
    
    if food_level <= threshold:
        return notify_low_food(user, food_level, threshold)
    
    return None


def notify_dispenser_cleaning(user: CustomUser, days: int = 3) -> Optional[Notification]:
    """Cria o lembrete para limpeza do comedouro."""
    title = "🧼 Limpeza do comedouro"
    message = (
        f"É hora de limpar o dispenser do seu pet. "
        f"O lembrete está configurado para a cada {days} dia(s)."
    )
    return create_notification(
        user=user,
        notification_type='dispenser_cleaning',
        title=title,
        message=message,
        send_email=True,
        send_push=True,
    )


def check_and_notify_dispenser_cleaning(user: CustomUser, days: int | None = None) -> Optional[Notification]:
    """Dispara lembrete de limpeza quando o intervalo configurado for atingido."""
    settings, _ = NotificationSettings.objects.get_or_create(user=user)
    reminder_days = days if days in (1, 2, 3, 4) else settings.dispenserCleaningReminderDays
    if reminder_days not in (1, 2, 3, 4):
        reminder_days = 3

    last_reminder = settings.lastDispenserCleaningReminderAt
    now = timezone.now()
    if last_reminder is None or now - last_reminder >= timedelta(days=reminder_days):
        notification = notify_dispenser_cleaning(user, reminder_days)
        if notification is not None:
            settings.lastDispenserCleaningReminderAt = now
            settings.dispenserCleaningReminderDays = reminder_days
            settings.save(update_fields=["lastDispenserCleaningReminderAt", "dispenserCleaningReminderDays"])
        return notification

    return None

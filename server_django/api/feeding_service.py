import logging
from datetime import datetime
from typing import List, Optional

from django.utils import timezone
from django.db.models import Q

from .iot_client import esp32_client
from .models import FeedingHistory, FeedingSchedule
from .notification_utils import check_and_notify_low_food, evaluate_feeding_pressure, notify_feeding_completed
from .servo_views import calculate_duration, update_device_status

logger = logging.getLogger(__name__)


def _schedule_matches_time(schedule: FeedingSchedule, now: datetime) -> bool:
    if not schedule.isActive:
        return False

    if not schedule.time:
        return False

    if schedule.frequency == "weekdays" and now.weekday() >= 5:
        return False
    if schedule.frequency == "weekends" and now.weekday() < 5:
        return False
    if schedule.frequency == "custom":
        allowed_days = set()
        raw_days = (schedule.daysOfWeek or "").replace(" ", "")
        if raw_days:
            for token in raw_days.split(","):
                if not token:
                    continue
                token_lower = token.lower()
                day_map = {
                    "sun": 6,
                    "mon": 0,
                    "tue": 1,
                    "wed": 2,
                    "thu": 3,
                    "fri": 4,
                    "sat": 5,
                }
                if token_lower in day_map:
                    allowed_days.add(day_map[token_lower])
                elif token.isdigit():
                    allowed_days.add(int(token) % 7)
        if raw_days and now.weekday() not in allowed_days:
            return False

    try:
        schedule_hour, schedule_minute = map(int, schedule.time.split(":", 1))
    except ValueError:
        logger.warning("Horário de agendamento inválido: %s", schedule.time)
        return False

    current_hour = now.hour
    current_minute = now.minute
    if schedule_hour != current_hour:
        return False
    return schedule_minute == current_minute


def execute_scheduled_feeding(schedule: FeedingSchedule, now: Optional[datetime] = None) -> bool:
    if now is None:
        now = timezone.now()

    pet = schedule.pet
    quantity = int(schedule.quantity or pet.defaultQuantity or 50)
    channel = pet.dispenser_channel

    if not esp32_client.is_online(channel=channel):
        logger.info(
            "Agendamento %s ignorado para o pet %s: dispositivo offline em %s",
            schedule.id,
            pet.id,
            now.isoformat(),
        )
        return False

    execution_window_start = now.replace(second=0, microsecond=0)
    execution_window_end = execution_window_start + timezone.timedelta(minutes=1)
    existing_execution = FeedingHistory.objects.filter(
        pet=pet,
        feedingType="scheduled",
        timestamp__gte=execution_window_start,
        timestamp__lt=execution_window_end,
        notes__icontains=f"Agendamento {schedule.id}",
    ).exists()
    if existing_execution:
        logger.info("Agendamento %s já executado nesta janela de tempo: %s", schedule.id, execution_window_start.isoformat())
        return False

    pressure_status = (esp32_client.get_status(channel) or {}) if channel is not None else {}
    pressure_percent = pressure_status.get("pressure_percent", 0)
    pressure_decision = evaluate_feeding_pressure(pet, pressure_percent=pressure_percent, elapsed_minutes=0)
    if pressure_decision["skip_next_portion"]:
        logger.info("Agendamento %s bloqueado para o pet %s porque o comedouro está cheio (pressão %.0f%%).", schedule.id, pet.id, pressure_percent)
        return False

    feeding_id = f"scheduled_{pet.id}_{schedule.id}_{int(now.timestamp())}"
    logger.info(
        "Executando agendamento %s para o pet %s às %s (quantidade %s g)",
        schedule.id,
        pet.id,
        now.isoformat(),
        quantity,
    )
    result = esp32_client.dispense_food(
        quantity=quantity,
        duration_ms=calculate_duration(quantity),
        feeding_id=feeding_id,
        channel=channel,
    )

    if not result.get("success"):
        error_message = result.get("error", "Unknown error")
        logger.warning("Falha no agendamento %s para o pet %s: %s", schedule.id, pet.id, error_message)
        FeedingHistory.objects.create(
            pet=pet,
            quantity=quantity,
            feedingType="scheduled",
            success=False,
            notes=f"Falha no agendamento {schedule.id}: {error_message}",
        )
        return False

    FeedingHistory.objects.create(
        pet=pet,
        quantity=quantity,
        feedingType="scheduled",
        success=True,
        notes=f"Agendamento {schedule.id} executado às {schedule.time}.",
    )
    logger.info("Agendamento %s concluído com sucesso para o pet %s", schedule.id, pet.id)
    update_device_status(pet.user, result)

    try:
        notify_feeding_completed(user=pet.user, pet_name=pet.name, quantity=quantity)
        food_level_after = result.get("food_level_after", 100)
        check_and_notify_low_food(pet.user, food_level_after)
    except Exception as exc:
        logger.warning("Falha ao enviar notificação do agendamento %s: %s", schedule.id, exc)

    return True


def process_due_schedules(now: Optional[datetime] = None) -> List[FeedingHistory]:
    if now is None:
        now = timezone.now()

    due_schedules = []
    for schedule in FeedingSchedule.objects.filter(isActive=True).select_related("pet"):
        if _schedule_matches_time(schedule, now):
            due_schedules.append(schedule)

    created_histories = []
    for schedule in due_schedules:
        executed = execute_scheduled_feeding(schedule, now=now)
        if executed:
            created_histories.append(FeedingHistory.objects.filter(pet=schedule.pet, feedingType="scheduled").latest("timestamp"))

    return created_histories

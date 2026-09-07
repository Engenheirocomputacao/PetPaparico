from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import DeviceStatus, FeedingHistory, FeedingSchedule, Notification, NotificationSettings, Pet
from .notification_utils import create_notification, evaluate_feeding_pressure


class EmptyStateUiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="sem_pet",
            email="sem_pet@example.com",
            password="senha123",
        )

    @patch("api.notification_utils.send_mail")
    def test_notification_creation_does_not_fail_when_user_has_no_settings(self, mock_send_mail):
        self.user.email = "user@example.com"
        self.user.save(update_fields=["email"])

        notification = create_notification(
            self.user,
            "feeding_completed",
            "Teste",
            "Mensagem de teste",
            send_email=True,
            send_push=False,
        )

        self.assertIsNotNone(notification)
        mock_send_mail.assert_called_once()

    def test_dashboard_shows_onboarding_for_user_without_pets(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("web_home"))

        self.assertContains(response, "Pronto para começar?")
        self.assertContains(response, "Cadastrar meu primeiro pet")
        self.assertContains(response, "Cadastre seu primeiro pet")

    def test_feeding_page_guides_user_when_no_pets_exist(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("web_feeding"))

        self.assertContains(response, "Você ainda não cadastrou nenhum pet")
        self.assertContains(response, "Cadastrar primeiro pet")

    def test_home_page_includes_vlibras_accessibility_script(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("web_home"))

        self.assertContains(response, "https://vlibras.gov.br/app/vlibras-plugin.js")

    def test_refill_creates_notification_for_authenticated_user(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("refill_food_container"),
            {"food_level": 100},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Notification.objects.filter(user=self.user).exists())
        self.assertEqual(Notification.objects.filter(user=self.user).count(), 1)

    def test_refill_handles_multiple_device_status_records_for_same_user(self):
        self.client.force_login(self.user)
        DeviceStatus.objects.create(user=self.user, channel=None, foodLevel=10, isOnline=True)
        DeviceStatus.objects.create(user=self.user, channel=1, foodLevel=30, isOnline=True)

        response = self.client.post(
            reverse("refill_food_container"),
            {"food_level": 100},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DeviceStatus.objects.filter(user=self.user, foodLevel=100).exists()
        )

    def test_delete_schedule_removes_selected_schedule(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        schedule = FeedingSchedule.objects.create(
            pet=pet,
            time="08:00",
            quantity=50,
            frequency="daily",
            isActive=True,
        )

        response = self.client.post(
            reverse("web_feeding"),
            {
                "pet_id": pet.id,
                "action": "delete_schedule",
                "schedule_id": schedule.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(FeedingSchedule.objects.filter(id=schedule.id).exists())

    def test_edit_schedule_updates_existing_schedule(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        schedule = FeedingSchedule.objects.create(
            pet=pet,
            time="08:00",
            quantity=50,
            frequency="daily",
            isActive=True,
        )

        response = self.client.post(
            reverse("web_feeding"),
            {
                "pet_id": pet.id,
                "action": "edit_schedule",
                "schedule_id": schedule.id,
                "time": "09:30",
                "schedule_quantity": 80,
                "frequency": "weekends",
            },
        )

        self.assertEqual(response.status_code, 302)
        schedule.refresh_from_db()
        self.assertEqual(schedule.time, "09:30")
        self.assertEqual(schedule.quantity, 80)
        self.assertEqual(schedule.frequency, "weekends")

    @patch("api.feeding_service.notify_feeding_completed")
    @patch("api.feeding_service.check_and_notify_low_food")
    @patch("api.feeding_service.esp32_client")
    def test_process_due_schedules_creates_scheduled_history(self, mock_client, mock_low_food, mock_notify):
        pet = Pet.objects.create(user=self.user, name="Luna", dispenser_channel=1)
        now = timezone.now().replace(second=0, microsecond=0)
        schedule = FeedingSchedule.objects.create(
            pet=pet,
            time=now.strftime("%H:%M"),
            quantity=60,
            frequency="daily",
            isActive=True,
        )

        mock_client.is_online.return_value = True
        mock_client.dispense_food.return_value = {"success": True, "food_level_after": 80}

        from .feeding_service import process_due_schedules

        created = process_due_schedules(now=now)

        self.assertEqual(len(created), 1)
        history = FeedingHistory.objects.get(pet=pet, feedingType="scheduled")
        self.assertEqual(history.quantity, 60)
        self.assertTrue(history.success)
        self.assertIn(str(schedule.id), history.notes)
        mock_notify.assert_called_once()
        mock_low_food.assert_called_once()

    @patch("api.feeding_service.notify_feeding_completed")
    @patch("api.feeding_service.check_and_notify_low_food")
    @patch("api.feeding_service.esp32_client")
    def test_process_due_schedules_does_not_duplicate_same_minute(self, mock_client, mock_low_food, mock_notify):
        pet = Pet.objects.create(user=self.user, name="Luna", dispenser_channel=2)
        now = timezone.now().replace(second=0, microsecond=0)
        FeedingSchedule.objects.create(
            pet=pet,
            time=now.strftime("%H:%M"),
            quantity=40,
            frequency="daily",
            isActive=True,
        )

        mock_client.is_online.return_value = True
        mock_client.dispense_food.return_value = {"success": True, "food_level_after": 70}

        from .feeding_service import process_due_schedules

        first_run = process_due_schedules(now=now)
        second_run = process_due_schedules(now=now)

        self.assertEqual(len(first_run), 1)
        self.assertEqual(len(second_run), 0)
        self.assertEqual(FeedingHistory.objects.filter(pet=pet, feedingType="scheduled").count(), 1)

    def test_cleaning_reminder_for_dispenser_triggers_every_selected_days(self):
        settings, _ = NotificationSettings.objects.get_or_create(user=self.user)
        settings.dispenserCleaningReminderDays = 2
        settings.lastDispenserCleaningReminderAt = timezone.now() - timedelta(days=2)
        settings.save(update_fields=["dispenserCleaningReminderDays", "lastDispenserCleaningReminderAt"])

        from .notification_utils import check_and_notify_dispenser_cleaning

        notification = check_and_notify_dispenser_cleaning(self.user)

        self.assertIsNotNone(notification)
        self.assertEqual(notification.type, "dispenser_cleaning")
        self.assertEqual(notification.user, self.user)

    def test_dashboard_shows_cleaning_pending_status(self):
        self.client.force_login(self.user)
        settings, _ = NotificationSettings.objects.get_or_create(user=self.user)
        settings.dispenserCleaningReminderDays = 3
        settings.lastDispenserCleaningReminderAt = timezone.now() - timedelta(days=4)
        settings.save(update_fields=["dispenserCleaningReminderDays", "lastDispenserCleaningReminderAt"])

        response = self.client.get(reverse("web_home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Limpeza pendente do comedouro")

    def test_mark_cleaned_creates_notification_in_history(self):
        self.client.force_login(self.user)
        settings, _ = NotificationSettings.objects.get_or_create(user=self.user)
        settings.dispenserCleaningReminderDays = 3
        settings.save(update_fields=["dispenserCleaningReminderDays"])

        response = self.client.post(
            reverse("web_dispenser_cleaning"),
            {"action": "mark_cleaned"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type="dispenser_cleaning",
                title__icontains="Limpeza",
            ).exists()
        )

    def test_notifications_page_can_mark_cleaning_done_directly(self):
        self.client.force_login(self.user)
        settings, _ = NotificationSettings.objects.get_or_create(user=self.user)
        settings.dispenserCleaningReminderDays = 2
        settings.save(update_fields=["dispenserCleaningReminderDays"])

        response = self.client.post(
            reverse("web_notifications"),
            {"action": "mark_cleaned"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                type="dispenser_cleaning",
                title__icontains="Comedouro",
            ).exists()
        )

    def test_pressure_sensor_notifies_when_pet_has_not_eaten_after_20_minutes(self):
        pet = Pet.objects.create(user=self.user, name="Luna", defaultQuantity=100)

        decision = evaluate_feeding_pressure(pet, pressure_percent=60, elapsed_minutes=20)

        self.assertTrue(decision["pet_did_not_eat"])
        self.assertFalse(decision["skip_next_portion"])
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                title__icontains="não se alimentou",
            ).exists()
        )

    def test_pressure_sensor_blocks_next_portion_when_dispenser_is_full(self):
        pet = Pet.objects.create(user=self.user, name="Luna", defaultQuantity=100)

        decision = evaluate_feeding_pressure(pet, pressure_percent=80, elapsed_minutes=5)

        self.assertTrue(decision["skip_next_portion"])
        self.assertFalse(decision["pet_did_not_eat"])
        self.assertTrue(
            Notification.objects.filter(
                user=self.user,
                title__icontains="Comedouro cheio",
            ).exists()
        )

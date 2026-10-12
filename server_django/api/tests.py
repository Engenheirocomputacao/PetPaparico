from datetime import date, datetime, time, timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
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

    def test_history_dashboard_shows_daily_chart_and_summary(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        FeedingHistory.objects.create(
            pet=pet,
            quantity=55,
            feedingType="manual",
            success=True,
        )

        response = self.client.get(
            reverse("web_history"),
            {"pet": pet.id, "filter": "day"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Histórico de alimentação")
        self.assertContains(response, "Últimas alimentações")
        self.assertContains(response, 'id="history-trend-chart"')
        self.assertContains(response, 'id="history-hour-chart"')
        self.assertContains(response, 'name="action" value="delete_feeding"')
        self.assertContains(response, "Excluir")
        self.assertContains(response, "history-hero")
        self.assertContains(response, "Como acontecem")
        self.assertEqual(response.context["chart_title"], "Consumo por horário")
        self.assertEqual(response.context["today_count"], 1)
        self.assertEqual(response.context["total_today"], 55)
        self.assertEqual(len(response.context["feedings_by_day_percent"]), 12)
        self.assertEqual(sum(response.context["feedings_by_hour"]), 55)
        self.assertEqual(response.context["feeding_type_counts"]["manual"], 1)
        self.assertEqual(
            sum(item["amount"] for item in response.context["feedings_by_day_percent"]),
            55,
        )

    def test_history_can_delete_a_feeding_from_the_selected_pet(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        feeding = FeedingHistory.objects.create(
            pet=pet,
            quantity=55,
            feedingType="manual",
            success=True,
        )

        response = self.client.post(
            reverse("web_history"),
            {
                "action": "delete_feeding",
                "feeding_id": feeding.id,
                "pet_id": pet.id,
                "filter": "day",
            },
        )

        self.assertRedirects(
            response,
            f"{reverse('web_history')}?pet={pet.id}&filter=day",
        )
        self.assertFalse(FeedingHistory.objects.filter(pk=feeding.pk).exists())

    def test_history_cannot_delete_a_feeding_from_another_tutor(self):
        self.client.force_login(self.user)
        selected_pet = Pet.objects.create(user=self.user, name="Luna")
        other_user = get_user_model().objects.create_user(
            username="outro_tutor_historico",
            password="test-password",
        )
        other_pet = Pet.objects.create(user=other_user, name="Toby")
        other_feeding = FeedingHistory.objects.create(
            pet=other_pet,
            quantity=55,
            feedingType="manual",
            success=True,
        )

        response = self.client.post(
            reverse("web_history"),
            {
                "action": "delete_feeding",
                "feeding_id": other_feeding.id,
                "pet_id": selected_pet.id,
                "filter": "day",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(FeedingHistory.objects.filter(pk=other_feeding.pk).exists())

    def test_history_dashboard_supports_each_period_filter(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        expected_titles = {
            "day": "Consumo por horário",
            "week": "Consumo por dia",
            "month": "Consumo por semana",
            "year": "Consumo por mês",
            "all": "Ritmo por dia da semana",
        }

        for period, expected_title in expected_titles.items():
            with self.subTest(period=period):
                response = self.client.get(
                    reverse("web_history"),
                    {"pet": pet.id, "filter": period},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["chart_title"], expected_title)

    def test_history_today_metrics_use_the_configured_local_timezone(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        feeding = FeedingHistory.objects.create(
            pet=pet,
            quantity=35,
            feedingType="manual",
            success=True,
        )
        local_midnight = timezone.localtime().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        FeedingHistory.objects.filter(pk=feeding.pk).update(
            timestamp=local_midnight + timedelta(minutes=30)
        )

        response = self.client.get(
            reverse("web_history"),
            {"pet": pet.id, "filter": "day"},
        )

        self.assertEqual(response.context["period_total"], 35)
        self.assertEqual(response.context["today_count"], 1)
        self.assertEqual(response.context["total_today"], 35)

    def test_history_month_chart_excludes_feedings_from_previous_month(self):
        self.client.force_login(self.user)
        pet = Pet.objects.create(user=self.user, name="Luna")
        current_feeding = FeedingHistory.objects.create(
            pet=pet,
            quantity=40,
            feedingType="manual",
            success=True,
        )
        previous_feeding = FeedingHistory.objects.create(
            pet=pet,
            quantity=90,
            feedingType="manual",
            success=True,
        )
        FeedingHistory.objects.filter(pk=previous_feeding.pk).update(
            timestamp=timezone.now() - timedelta(days=40)
        )

        response = self.client.get(
            reverse("web_history"),
            {"pet": pet.id, "filter": "month"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sum(item["amount"] for item in response.context["feedings_by_day_percent"]),
            current_feeding.quantity,
        )

    def test_notifications_can_be_deleted_for_an_inclusive_date_range(self):
        self.client.force_login(self.user)
        start_date = timezone.localdate() - timedelta(days=1)
        end_date = timezone.localdate()
        outside_date = end_date + timedelta(days=1)
        own_notifications = [
            Notification.objects.create(
                user=self.user,
                type="general",
                title=f"Alerta {index}",
                message="Teste",
            )
            for index in range(3)
        ]
        local_timezone = timezone.get_current_timezone()
        for notification, sent_date in zip(
            own_notifications,
            (start_date, end_date, outside_date),
        ):
            sent_at = timezone.make_aware(
                datetime.combine(sent_date, time(hour=12)),
                local_timezone,
            )
            Notification.objects.filter(pk=notification.pk).update(sentAt=sent_at)

        other_user = get_user_model().objects.create_user(
            username="outro_tutor",
            password="test-password",
        )
        other_notification = Notification.objects.create(
            user=other_user,
            type="general",
            title="Alerta de outro tutor",
            message="Não deve ser removido",
        )

        response = self.client.post(
            reverse("web_notifications"),
            {
                "action": "delete_notifications_range",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        self.assertRedirects(response, reverse("web_notifications"))
        self.assertFalse(Notification.objects.filter(pk=own_notifications[0].pk).exists())
        self.assertFalse(Notification.objects.filter(pk=own_notifications[1].pk).exists())
        self.assertTrue(Notification.objects.filter(pk=own_notifications[2].pk).exists())
        self.assertTrue(Notification.objects.filter(pk=other_notification.pk).exists())

    def test_notifications_date_range_rejects_an_end_date_before_the_start(self):
        self.client.force_login(self.user)
        notification = Notification.objects.create(
            user=self.user,
            type="general",
            title="Alerta preservado",
            message="Não deve ser removido",
        )

        response = self.client.post(
            reverse("web_notifications"),
            {
                "action": "delete_notifications_range",
                "start_date": timezone.localdate().isoformat(),
                "end_date": (timezone.localdate() - timedelta(days=1)).isoformat(),
            },
        )

        self.assertRedirects(response, reverse("web_notifications"))
        self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())

    @patch("api.web_views.check_and_notify_dispenser_cleaning")
    def test_notifications_page_shows_date_range_and_single_item_actions(self, mock_cleaning):
        self.client.force_login(self.user)
        Notification.objects.create(
            user=self.user,
            type="general",
            title="Alerta de teste",
            message="Notificação de exemplo",
        )

        response = self.client.get(reverse("web_notifications"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="start_date"')
        self.assertContains(response, 'name="end_date"')
        self.assertContains(response, "Excluir período")
        self.assertContains(response, "Marcar lida")
        self.assertContains(response, "Excluir")
        mock_cleaning.assert_called_once_with(self.user)

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


class GenerateFeedingHistoryCommandTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="history_generator",
            email="history_generator@example.com",
            password="test-password",
        )
        self.quantities = {}
        for index, name in enumerate(("Bolt", "Catão", "Dog", "Koriane"), start=1):
            pet = Pet.objects.create(user=self.user, name=name)
            self.quantities[name] = (index * 10, index * 10 + 5)
            morning_time = "08:05" if name == "Koriane" else "08:00"
            for feeding_time, quantity in zip(
                (morning_time, "18:00"), self.quantities[name]
            ):
                FeedingSchedule.objects.create(
                    pet=pet,
                    time=feeding_time,
                    quantity=quantity,
                    frequency="daily",
                    isActive=True,
                )

    def run_generator(self, *, start_date, end_date, apply=False):
        output = StringIO()
        call_command(
            "generate_feeding_history",
            start_date=start_date,
            end_date=end_date,
            apply=apply,
            stdout=output,
        )
        return output.getvalue()

    def test_generates_two_daily_records_using_each_schedule_quantity(self):
        output = self.run_generator(
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 2),
            apply=True,
        )

        self.assertEqual(FeedingHistory.objects.count(), 16)
        for history in FeedingHistory.objects.select_related("pet"):
            local_timestamp = timezone.localtime(history.timestamp)
            self.assertIn(local_timestamp.date(), {date(2026, 9, 1), date(2026, 9, 2)})
            if local_timestamp.hour == 8:
                self.assertEqual(history.quantity, self.quantities[history.pet.name][0])
            else:
                self.assertEqual(local_timestamp.hour, 18)
                self.assertEqual(history.quantity, self.quantities[history.pet.name][1])
            self.assertEqual(history.timestamp.minute, 0)
            self.assertEqual(history.feedingType, "scheduled")
            self.assertTrue(history.success)
            self.assertIn("[SIMULATED]", history.notes)
        self.assertIn("Nenhum dispensador foi acionado", output)

    def test_running_generator_twice_does_not_duplicate_history(self):
        arguments = {
            "start_date": date(2026, 9, 1),
            "end_date": date(2026, 9, 1),
            "apply": True,
        }
        self.run_generator(**arguments)
        self.run_generator(**arguments)

        self.assertEqual(FeedingHistory.objects.count(), 8)

    def test_preview_does_not_write_history(self):
        output = self.run_generator(
            start_date=date(2026, 9, 1),
            end_date=date(2026, 9, 1),
        )

        self.assertEqual(FeedingHistory.objects.count(), 0)
        self.assertIn("Use --apply", output)

    def test_requires_daily_active_schedules_at_both_times(self):
        FeedingSchedule.objects.filter(
            pet__name="Bolt",
            time="18:00",
        ).update(frequency="weekends")

        with self.assertRaisesMessage(CommandError, "frequência diária"):
            self.run_generator(
                start_date=date(2026, 9, 1),
                end_date=date(2026, 9, 1),
            )

import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.feeding_service import process_due_schedules

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Processa agendamentos de alimentação que devem ocorrer no horário atual"

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=1, help="Intervalo em minutos para verificar agendamentos")

    def handle(self, *args, **options):
        logger.info("Iniciando processamento de agendamentos")
        while True:
            now = timezone.now()
            process_due_schedules(now=now)
            self.stdout.write(self.style.SUCCESS(f"Verificado em {now:%H:%M:%S}"))
            self.stdout.flush()
            self._sleep(options["minutes"])

    def _sleep(self, minutes: int):
        import time
        time.sleep(minutes * 60)

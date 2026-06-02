from django.core.management.base import BaseCommand, CommandError

from services.bot_bridge import confirm_order, writes_enabled


class Command(BaseCommand):
    help = "Confirma un pedido reutilizando OrderService/AdminService del bot."

    def add_arguments(self, parser):
        parser.add_argument("order_id", type=str, help="ID del pedido, ej. ORD-A1B2C3D4")

    def handle(self, *args, **options):
        if not writes_enabled():
            raise CommandError(
                "DASHBOARD_ENABLE_WRITES=0. Activa escrituras en .env.dashboard para usar este comando."
            )

        result = confirm_order(options["order_id"])
        if result.ok:
            self.stdout.write(self.style.SUCCESS(result.message))
            return
        if result.already_confirmed:
            self.stdout.write(self.style.WARNING(result.message))
            return
        raise CommandError(result.message)

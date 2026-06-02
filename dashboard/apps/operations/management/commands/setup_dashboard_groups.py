from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from apps.operations.permissions import GROUP_ADMIN, GROUP_OPERATOR


class Command(BaseCommand):
    help = "Crea grupos dashboard_operator y dashboard_admin para permisos del panel."

    def add_arguments(self, parser):
        parser.add_argument(
            "--assign",
            type=str,
            default="",
            help="Usuario Django al que asignar dashboard_admin (opcional).",
        )
        parser.add_argument(
            "--operator",
            type=str,
            default="",
            help="Usuario Django al que asignar dashboard_operator (opcional).",
        )

    def handle(self, *args, **options):
        operator_group, _ = Group.objects.get_or_create(name=GROUP_OPERATOR)
        admin_group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
        self.stdout.write(self.style.SUCCESS(f"Grupo {GROUP_OPERATOR} listo."))
        self.stdout.write(self.style.SUCCESS(f"Grupo {GROUP_ADMIN} listo."))

        assign_admin = options.get("assign", "").strip()
        assign_operator = options.get("operator", "").strip()

        if assign_admin:
            user = User.objects.filter(username=assign_admin).first()
            if not user:
                self.stdout.write(self.style.ERROR(f"Usuario no encontrado: {assign_admin}"))
            else:
                user.groups.add(admin_group, operator_group)
                self.stdout.write(
                    self.style.SUCCESS(f"{assign_admin} → admin + operador.")
                )

        if assign_operator:
            user = User.objects.filter(username=assign_operator).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR(f"Usuario no encontrado: {assign_operator}")
                )
            else:
                user.groups.add(operator_group)
                self.stdout.write(
                    self.style.SUCCESS(f"{assign_operator} → operador.")
                )

        self.stdout.write(
            "Operador: pedidos, clientes, disponibilidad menú. "
            "Admin: CRUD menú, eliminar clientes, configuración."
        )

from __future__ import annotations

import json

from django import forms

from apps.operations.services import readers
from services import bot_bridge


class MenuItemForm(forms.Form):
    item_id = forms.CharField(label="ID", max_length=32, widget=forms.TextInput(attrs={"class": "input"}))
    nombre = forms.CharField(label="Nombre", max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
    precio = forms.DecimalField(
        label="Precio (€)",
        min_value=0.01,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
    )
    categoria = forms.CharField(label="Categoría", max_length=80, widget=forms.TextInput(attrs={"class": "input"}))
    disponible = forms.BooleanField(label="Disponible", required=False, initial=True)

    def __init__(self, *args, is_new: bool = False, **kwargs):
        self.is_new = is_new
        super().__init__(*args, **kwargs)
        if not is_new:
            self.fields["item_id"].widget.attrs["readonly"] = True

    def clean_item_id(self):
        item_id = self.cleaned_data["item_id"].strip()
        if not item_id:
            raise forms.ValidationError("El ID es obligatorio.")
        existing_ids = {
            str(i.get("id", "")).strip()
            for i in readers.read_menu()
            if i.get("id")
        }
        if self.is_new and item_id in existing_ids:
            raise forms.ValidationError(f"Ya existe un plato con ID {item_id}.")
        if not self.is_new and item_id not in existing_ids:
            raise forms.ValidationError(f"No encontré el plato {item_id}.")
        return item_id


class OrderCreateForm(forms.Form):
    wa_id = forms.CharField(label="WA ID", max_length=64, widget=forms.TextInput(attrs={"class": "input"}))
    customer_name = forms.CharField(
        label="Nombre cliente", max_length=120, required=False, widget=forms.TextInput(attrs={"class": "input"})
    )
    address = forms.CharField(
        label="Dirección",
        max_length=240,
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "class": "input"}),
    )
    delivery_type = forms.ChoiceField(
        label="Tipo entrega",
        choices=[("", "—"), ("domicilio", "Domicilio"), ("recoger", "Recoger en tienda")],
        required=False,
        widget=forms.Select(attrs={"class": "input"}),
    )
    items_json = forms.CharField(
        label="Ítems (JSON)",
        widget=forms.Textarea(
            attrs={
                "rows": 8,
                "class": "input",
                "placeholder": '[{"product":"Pizza Margarita","qty":2,"unit_price":11.0}]',
            }
        ),
    )

    def clean_wa_id(self):
        wa_id = self.cleaned_data["wa_id"].strip()
        error = bot_bridge._validate_wa_id(wa_id)
        if error:
            raise forms.ValidationError(error)
        return wa_id

    def clean_items_json(self):
        items, error = bot_bridge.parse_order_items_json(self.cleaned_data["items_json"])
        if error:
            raise forms.ValidationError(error)
        self.cleaned_items = items
        return self.cleaned_data["items_json"]


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(
        label="Estado",
        choices=[(s, s.capitalize()) for s in readers.ORDER_STATUSES],
        widget=forms.Select(attrs={"class": "input"}),
    )


class OrderItemsForm(forms.Form):
    items_json = forms.CharField(
        label="Ítems (JSON)",
        widget=forms.Textarea(attrs={"rows": 8, "class": "input"}),
    )

    def __init__(self, *args, initial_items=None, **kwargs):
        super().__init__(*args, **kwargs)
        if initial_items is not None and not self.initial.get("items_json"):
            self.initial["items_json"] = json.dumps(initial_items, ensure_ascii=False, indent=2)

    def clean_items_json(self):
        items, error = bot_bridge.parse_order_items_json(self.cleaned_data["items_json"])
        if error:
            raise forms.ValidationError(error)
        self.cleaned_items = items
        return self.cleaned_data["items_json"]


class CustomerForm(forms.Form):
    wa_id = forms.CharField(label="WA ID", max_length=64, widget=forms.TextInput(attrs={"class": "input"}))
    name = forms.CharField(label="Nombre", max_length=120, widget=forms.TextInput(attrs={"class": "input"}))
    notes = forms.CharField(
        label="Notas (solo panel)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "class": "input"}),
    )

    def __init__(self, *args, is_new: bool = False, **kwargs):
        self.is_new = is_new
        super().__init__(*args, **kwargs)
        if not is_new:
            self.fields["wa_id"].widget.attrs["readonly"] = True

    def clean_wa_id(self):
        wa_id = self.cleaned_data["wa_id"].strip()
        error = bot_bridge._validate_wa_id(wa_id)
        if error:
            raise forms.ValidationError(error)
        existing = readers.read_user(wa_id)
        if self.is_new and existing:
            raise forms.ValidationError(f"Ya existe un cliente con WA ID {wa_id}.")
        if not self.is_new and not existing:
            raise forms.ValidationError(f"No encontré el cliente {wa_id}.")
        return wa_id


class PanelStaffForm(forms.Form):
    """Django users with dashboard_operator / dashboard_admin groups."""

    ROLE_OPERATOR = "operator"
    ROLE_ADMIN = "admin"

    username = forms.CharField(
        label="Usuario",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "input", "autocomplete": "username"}),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"class": "input", "autocomplete": "email"}),
    )
    role = forms.ChoiceField(
        label="Rol del panel",
        choices=[
            (ROLE_OPERATOR, "Operador (pedidos, clientes, menú disponibilidad)"),
            (ROLE_ADMIN, "Admin (CRUD menú, eliminar clientes, configuración)"),
        ],
        widget=forms.Select(attrs={"class": "input"}),
    )
    is_active = forms.BooleanField(label="Activo", required=False, initial=True)
    password1 = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        required=False,
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "new-password"}),
    )

    def __init__(self, *args, is_new: bool = False, **kwargs):
        self.is_new = is_new
        super().__init__(*args, **kwargs)
        if not is_new:
            self.fields["password1"].required = False
            self.fields["password2"].required = False
            self.fields["password1"].help_text = "Dejar vacío para no cambiar la contraseña."
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

    def clean_username(self):
        from django.contrib.auth.models import User

        username = self.cleaned_data["username"].strip()
        if not username:
            raise forms.ValidationError("El usuario es obligatorio.")
        exists = User.objects.filter(username=username).exists()
        if self.is_new and exists:
            raise forms.ValidationError("Ese nombre de usuario ya existe.")
        if not self.is_new and not exists:
            raise forms.ValidationError("Usuario no encontrado.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1", "")
        p2 = cleaned.get("password2", "")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            elif len(p1) < 8:
                self.add_error("password1", "Mínimo 8 caracteres.")
        elif self.is_new:
            self.add_error("password1", "La contraseña es obligatoria al crear.")
        return cleaned


class PanelSettingsForm(forms.Form):
    """Operative preferences stored in accounts.DashboardSettings (PostgreSQL)."""

    default_order_status_filter = forms.ChoiceField(
        label="Filtro pedidos por defecto",
        choices=[("", "Todos")] + [(s, s.capitalize()) for s in readers.ORDER_STATUSES],
        required=False,
        widget=forms.Select(attrs={"class": "input"}),
    )
    orders_per_page = forms.IntegerField(
        label="Pedidos por página",
        min_value=5,
        max_value=100,
        initial=20,
        widget=forms.NumberInput(attrs={"class": "input"}),
    )
    show_cancelled_orders = forms.BooleanField(
        label="Mostrar cancelados en listado", required=False, initial=True
    )
    panel_notes = forms.CharField(
        label="Notas operativas del panel",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "input"}),
    )

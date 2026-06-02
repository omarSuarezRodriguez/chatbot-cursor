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

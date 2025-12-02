from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

ORDER_TYPE_CHOICES = (
    ("BUY", "Achat"),
    ("SELL", "Vente"),
)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control form-control-sm")


class OrderForm(forms.Form):
    symbol = forms.CharField(label="Symbole", max_length=10)
    type = forms.ChoiceField(label="Type d'ordre", choices=ORDER_TYPE_CHOICES)
    quantity = forms.IntegerField(label="Quantité", min_value=1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["symbol"].widget.attrs.setdefault("class", "form-control form-control-sm")
        self.fields["type"].widget.attrs.setdefault("class", "form-select form-select-sm")
        self.fields["quantity"].widget.attrs.setdefault("class", "form-control form-control-sm")


class CashOperationForm(forms.Form):
    TYPE_CHOICES = (
        ("IN", "Dépôt de cash"),
        ("OUT", "Retrait de cash"),
    )

    type = forms.ChoiceField(label="Type d'opération", choices=TYPE_CHOICES)

    amount = forms.DecimalField(label="Montant", min_value=0.01, max_digits=12, decimal_places=2)
    note = forms.CharField(label="Note", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].widget.attrs.setdefault("class", "form-select form-select-sm")
        self.fields["amount"].widget.attrs.setdefault("class", "form-control form-control-sm")
        self.fields["note"].widget.attrs.setdefault("class", "form-control form-control-sm")

class SymbolSearchForm(forms.Form):
    query = forms.CharField(label="Symbole ou nom", max_length=50)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["query"].widget.attrs.setdefault(
            "class", "form-control form-control-sm"
        )
        self.fields["query"].widget.attrs.setdefault(
            "placeholder", "Ex: TSLA, Apple, Microsoft..."
        )

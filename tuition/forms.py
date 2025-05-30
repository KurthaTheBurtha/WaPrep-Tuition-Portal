from django import forms
from .models import AccountRequest, User

class AccountRequestForm(forms.ModelForm):
    class Meta:
        model = AccountRequest
        fields = ['first_name', 'last_name', 'email', 'contact_info']

class PayerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']

class EditPayerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'contact_info']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'contact_info': forms.Textarea(attrs={'rows': 2}),
        }
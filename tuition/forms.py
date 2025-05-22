from django import forms
from .models import AccountRequest, User

class AccountRequestForm(forms.ModelForm):
    class Meta:
        model = AccountRequest
        fields = ['first_name', 'last_name', 'child_first_name', 'child_last_name', 'email', 'contact_info']

class ParentProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address']

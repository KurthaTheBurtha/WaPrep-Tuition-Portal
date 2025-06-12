from django import forms
from .models import AccountRequest, User

class AccountRequestForm(forms.ModelForm):
    class Meta:
        model = AccountRequest
        fields = ['first_name', 'last_name', 'email', 'contact_info']

class PayerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'contact_info']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'contact_info': forms.Textarea(attrs={'rows': 2}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'e.g., (555) 555-5555'}),
        }

class EditPayerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'address', 'contact_info']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 2}),
            'contact_info': forms.Textarea(attrs={'rows': 2}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'e.g., (555) 555-5555'}),
        }
        
class QuestionForm(forms.Form):
    subject = forms.CharField(max_length=100)
    students = forms.MultipleChoiceField(choices=[], required=False)
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, student_choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['students'].choices = student_choices
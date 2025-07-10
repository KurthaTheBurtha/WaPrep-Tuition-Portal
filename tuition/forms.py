from django import forms
from .models import AccountRequest, User, BankAccount
from .utils import validate_password, get_password_strength

class AccountRequestForm(forms.ModelForm):
    class Meta:
        model = AccountRequest
        fields = ['first_name', 'last_name', 'email', 'student_names']
        widgets = {
            'student_names': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter the names of all students you are responsible for (e.g., John Smith, Jane Smith)',
                'required': True
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required
        for field_name in self.fields:
            self.fields[field_name].required = True

class QuestionForm(forms.Form):
    subject = forms.CharField(max_length=100)
    students = forms.MultipleChoiceField(choices=[], required=False)
    message = forms.CharField(widget=forms.Textarea)

    def __init__(self, student_choices, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['students'].choices = student_choices

class BankAccountForm(forms.ModelForm):
    class Meta:
        model = BankAccount
        fields = ['nickname']
        widgets = {
            'nickname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., My Checking Account'
            })
        }

class BankAccountPaymentForm(forms.Form):
    """Form for processing payments with bank accounts"""
    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        empty_label="Select a bank account",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.HiddenInput()
    )
    student_id = forms.IntegerField(widget=forms.HiddenInput())
    
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bank_account'].queryset = BankAccount.objects.filter(user=user)



class PayerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class EditPayerProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


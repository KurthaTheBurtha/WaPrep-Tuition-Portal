from django import forms
from .models import AccountRequest, User

class AccountRequestForm(forms.ModelForm):
    class Meta:
        model = AccountRequest
        fields = ['first_name', 'last_name', 'email', 'contact_info']

class ProfileCompletionForm(forms.ModelForm):
    """
    Form for completing user profile after activation.
    Requires password change and contact information.
    """
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Enter your new password'
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Enter the same password as above, for verification'
    )
    
    class Meta:
        model = User
        fields = ['phone_number', 'address', 'contact_info']
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., (555) 555-5555',
                'required': True
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter your full address',
                'required': True
            }),
            'contact_info': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional contact information (optional)'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 != new_password2:
                raise forms.ValidationError("The two password fields didn't match.")
            
            # Validate password strength
            if len(new_password1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
        
        return cleaned_data
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number:
            raise forms.ValidationError("Phone number is required.")
        return phone_number
    
    def clean_address(self):
        address = self.cleaned_data.get('address')
        if not address:
            raise forms.ValidationError("Address is required.")
        return address

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
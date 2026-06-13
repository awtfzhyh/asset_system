from django import forms
from .models import Request

class BorrowRequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['return_date', 'remarks'] 
        widgets = {
            'return_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['user_name', 'phone', 'email', 'return_date', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'placeholder': 'Condition of asset...', 'class': 'form-control', 'rows': 3}),
        }

class ExtendRequestForm(forms.ModelForm):
    class Meta:
        model = Request
        # These fields MUST match the names used in your views.py and HTML
        fields = [
            'user_name', 
            'phone', 
            'email', 
            'return_date', 
            'purpose'
        ]
        
        # Optional: Add widgets to match your Bootstrap styling automatically
        widgets = {
            'user_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'return_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
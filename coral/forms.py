from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Contact


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['tipo_contato', 'assunto', 'mensagem']
        widgets = {
            'tipo_contato': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'assunto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título da mensagem',
                'required': True
            }),
            'mensagem': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descreva sua mensagem...',
                'rows': 6,
                'required': True
            }),
        }


class CustomUserCreationForm(UserCreationForm):
    nome_completo = forms.CharField(label='Nome Completo', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu nome completo'}))
    email = forms.EmailField(label='Email', required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control',
        'placeholder': 'seu@email.com'
    }))
    
    class Meta:
        model = User
        fields = ('username', 'nome_completo', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome de usuário'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].label = 'Senha'
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Senha'})
        self.fields['password2'].label = 'Confirme a senha'
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirme a senha'})
        self.fields['username'].label = 'Nome de usuário'
    
    def save(self, commit=True):
        user = super().save(commit=False)
        nome_completo = self.cleaned_data['nome_completo'].split(' ', 1)
        user.first_name = nome_completo[0]
        user.last_name = nome_completo[1] if len(nome_completo) > 1 else ''
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email já está cadastrado.")
        return email

class UserUpdateForm(forms.ModelForm):
    nome_completo = forms.CharField(label='Nome Completo', required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu nome completo'}))
    new_password = forms.CharField(label='Nova Senha', required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Deixe em branco para manter a atual'}))
    confirm_password = forms.CharField(label='Confirme a Nova Senha', required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirme a nova senha'}))

    class Meta:
        model = User
        fields = ('nome_completo',)
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            kwargs.setdefault('initial', {})['nome_completo'] = instance.get_full_name()
        super().__init__(*args, **kwargs)
        
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm = cleaned_data.get("confirm_password")
        if password and password != confirm:
            raise forms.ValidationError("As senhas não coincidem.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        nome_completo = self.cleaned_data['nome_completo'].split(' ', 1)
        user.first_name = nome_completo[0]
        user.last_name = nome_completo[1] if len(nome_completo) > 1 else ''
        
        password = self.cleaned_data.get('new_password')
        if password:
            user.set_password(password)
            
        if commit:
            user.save()
        return user

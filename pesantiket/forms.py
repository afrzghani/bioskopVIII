from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Film, Jadwal, User



class RegisterForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'class': 'form-control'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email', 'class': 'form-control'})
    )
    nama = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Nama Lengkap', 'class': 'form-control'})
    )
    noTelepon = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Nomor Telepon', 'class': 'form-control'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-control'})
    )
    password2 = forms.CharField(
        label="Konfirmasi Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Konfirmasi Password', 'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'nama', 'noTelepon', 'password1', 'password2']
        

        
class FilmForm(forms.ModelForm):
    class Meta:
        model = Film
        fields = '__all__'

class JadwalForm(forms.ModelForm):
    class Meta:
        model = Jadwal
        fields = '__all__'

    
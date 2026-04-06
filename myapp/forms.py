"""
myapp/forms.py
==============
Demonstrates:
 - ModelForm  (tied to ORM model)
 - Plain Form  (manual field definition)
 - Custom validation
 - Widget customisation
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Post, Comment, Category, Tag


# ──────────────────────────────────────────
# Registration Form
# ──────────────────────────────────────────
class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50)
    last_name = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email',
                  'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email


# ──────────────────────────────────────────
# Styled Login Form  (wraps AuthenticationForm)
# ──────────────────────────────────────────
class StyledLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


# ──────────────────────────────────────────
# Post Form  (ModelForm)
# ──────────────────────────────────────────
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'slug', 'body', 'category', 'tags', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Post title'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.CheckboxSelectMultiple(),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '')
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")
        return title


# ──────────────────────────────────────────
# Comment Form
# ──────────────────────────────────────────
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']
        widgets = {
            'body': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your comment…',
            }),
        }
        labels = {'body': 'Your Comment'}


# ──────────────────────────────────────────
# Contact Form  (no model, plain Form)
# ──────────────────────────────────────────
class ContactForm(forms.Form):
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('bug', 'Bug Report'),
        ('feature', 'Feature Request'),
    ]
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    message = forms.CharField(
        min_length=10,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
    )

    def clean_message(self):
        msg = self.cleaned_data.get('message', '')
        forbidden = ['spam', 'advertisement']
        for word in forbidden:
            if word in msg.lower():
                raise forms.ValidationError("Message contains forbidden content.")
        return msg


# ──────────────────────────────────────────
# Search Form
# ──────────────────────────────────────────
class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search posts…'}),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label='All Categories',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
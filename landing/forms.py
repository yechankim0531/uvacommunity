from django import forms
from .models import Community


class FileUploadForm(forms.Form):
    file = forms.FileField()


class FileUploadForm(forms.Form):
    file = forms.FileField()
    title = forms.CharField(max_length=255, help_text="Enter a title for the file.")
    description = forms.CharField(
        widget=forms.Textarea, help_text="Enter a description of the file contents."
    )
    keywords = forms.CharField(help_text="Enter keywords separated by commas.")

class CommunityForm(forms.Form):
    name = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea)
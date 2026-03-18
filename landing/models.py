from django.contrib.auth.models import User
from django.db import models
from django import forms
from django.utils import timezone
from django.utils.timezone import now


class Community(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=1000)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    tags = models.TextField()

    def __str__(self):
        return self.name


class CommunityJoinRequest(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE
    )  # The user making the request
    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="join_requests"
    )  # The community being requested
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    request_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} requests to join {self.community.name} - {self.status}"


class Member(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(
        Community, related_name="members", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("user", "community")

    def __str__(self):
        return self.name


class CommunityForm(forms.ModelForm):
    class Meta:
        model = Community
        fields = ["name", "description", "tags"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Community Name"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Description"}
            ),
            "tags": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Tags (comma-separated)"}
            ),
        }


class AddMemberForm(forms.Form):
    member = forms.ModelChoiceField(
        queryset=User.objects.all(), label="Select a user to add"
    )

    def __init__(self, *args, **kwargs):
        community = kwargs.pop("community", None)
        super(AddMemberForm, self).__init__(*args, **kwargs)
        if community:
            # Exclude users who are already members of the community
            self.fields["member"].queryset = User.objects.exclude(
                pk__in=community.members.all()
            )


class Event(models.Model):
    EVENT_TYPES = [
        ("social", "Social"),
        ("career", "Career Development"),
        ("comp", "Competition"),
        ("cultural", "Cultural"),
        ("volunteer", "Volunteer"),
        ("private", "Members Only"),
    ]

    name = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField()
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES)
    location = models.CharField(max_length=200)
    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="events"
    )
    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ["name", "location", "date", "description", "event_type"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Event Name"}
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Location"}
            ),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "description": forms.Textarea(
                attrs={"class": "form-control", "placeholder": "Description"}
            ),
            "event_type": forms.Select(attrs={"class": "form-control"}),
        }

    # to disallow users from creating an event in the past
    def clean_date(self):
        event_date = self.cleaned_data.get("date")
        if event_date and event_date < now().date():  # Compare with today's date
            raise forms.ValidationError("The event date cannot be in the past.")
        return event_date


class EventRSVP(models.Model):
    ATTENDANCE_CHOICES = [
        ("attending", "Attending"),
        ("not_attending", "Not Attending"),
    ]

    event = models.ForeignKey("Event", on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=ATTENDANCE_CHOICES)

    class Meta:
        unique_together = ("event", "user")  # Each user can RSVP once per event

    def __str__(self):
        return f"{self.user.username} - {self.status}"


class File(models.Model):
    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="files"
    )
    title = models.CharField(max_length=255)
    file_url = models.CharField(max_length=255)
    upload_timestamp = models.DateTimeField(default=timezone.now)
    description = models.TextField()
    keywords = models.CharField(max_length=255)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE)

    def keyword_list(self):
        return [
            keyword.strip() for keyword in self.keywords.split(",") if keyword.strip()
        ]

    def __str__(self):
        return self.title


class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    community = models.ForeignKey(
        Community, on_delete=models.CASCADE, related_name="chat_messages"
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

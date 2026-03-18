from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
import boto3
from .forms import FileUploadForm
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.urls import reverse
from .models import (
    Community,
    CommunityForm,
    CommunityJoinRequest,
    Member,
    Event,
    EventForm,
    EventRSVP,
    File,
    ChatMessage,
)
from django.db.models import Q
from django.utils.timezone import now


# @login_required
def landing_page(request):
    search_query = request.GET.get("search", "")  # Get the search term from the request
    communities = Community.objects.filter(
        Q(name__icontains=search_query) | Q(tags__icontains=search_query)
    )

    # Check if the user is in the PMA group
    is_pma = request.user.groups.filter(name="PMA").exists()
    for community in communities:
        community.tags_list = [tag.strip() for tag in community.tags.split(",")]
        if request.user.is_authenticated:
            if is_pma:
                # PMA members can view all communities without joining
                community.is_member = True
            else:
                # Regular users must join to view
                community.is_member = community.members.filter(
                    user=request.user
                ).exists()

            # Check if the user has sent a join request and if it's still pending
            if not community.is_member and not is_pma:
                community.join_request = CommunityJoinRequest.objects.filter(
                    user=request.user, community=community, status="pending"
                ).first()
            else:
                community.join_request = None
        else:
            # Defaults for unauthenticated users
            community.is_member = False
            community.join_request = None

    return render(
        request,
        "landing/landing.html",
        {
            "communities": communities,
            "is_pma": is_pma,
            "search_query": search_query,
            "is_authenticated": request.user.is_authenticated,
        },
    )


def join_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    existing_request = CommunityJoinRequest.objects.filter(
        user=request.user, community=community, status="pending"
    ).first()

    if existing_request:
        messages.info(
            request,
            "You already have a pending request to join this community. Please wait for approval.",
        )
    else:
        CommunityJoinRequest.objects.create(
            user=request.user, community=community, status="pending"
        )
        messages.success(
            request,
            "Your request to join the community has been submitted. Please wait for approval.",
        )

    return redirect("landing")


def exit_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if community.creator != request.user:
        if request.method == "POST":
            member = get_object_or_404(Member, user=request.user, community=community)
            member.delete()

            existing_request = CommunityJoinRequest.objects.filter(
                user=request.user, community=community, status="pending"
            ).first()
            if existing_request:
                existing_request.delete()

            messages.success(request, "You have successfully exited the community.")
            return redirect("landing")

        return render(
            request, "community/exit_confirmation.html", {"community": community}
        )

    messages.error(
        request,
        "As the creator, you cannot exit the community. Please delete the community first if necessary.",
    )
    return redirect("community_detail", community_id=community.id)


def requests_page(request):
    if request.user.groups.filter(name="PMA").exists():
        return render(request, "login/PMA.html")
    if not request.user.is_authenticated:
        return render(request, "login/login.html")
    outgoing_requests = CommunityJoinRequest.objects.filter(user=request.user)
    incoming_requests = CommunityJoinRequest.objects.filter(
        community__creator=request.user, status="pending"
    )

    return render(
        request,
        "requests/requests.html",
        {
            "outgoing_requests": outgoing_requests,
            "incoming_requests": incoming_requests,
        },
    )


def handle_join_request(request, request_id, action):
    join_request = get_object_or_404(CommunityJoinRequest, id=request_id)

    if not request.user.is_authenticated:
        messages.info(request, "You need to log in to join the community.")
        return redirect("login")

    # Only allow the community creator to manage requests
    if request.user == join_request.community.creator:
        if action == "accept":
            # Check if the user is already a member
            if not Member.objects.filter(
                user=join_request.user, community=join_request.community
            ).exists():
                # Add the user to the community
                Member.objects.create(
                    user=join_request.user, community=join_request.community
                )
            join_request.status = "accepted"
        elif action == "reject":
            join_request.status = "rejected"
        join_request.save()

    return redirect("requests_page")


@login_required
def community_detail(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    is_member = community.members.filter(user=request.user).exists()
    is_pma = request.user.groups.filter(name="PMA").exists()
    is_creator = request.user == community.creator
    members = community.members.select_related("user")
    messages = ChatMessage.objects.filter(community=community).order_by("timestamp")

    if request.method == "POST":
        message_text = request.POST.get("message")
        if message_text and request.user.is_authenticated:
            ChatMessage.objects.create(
                user=request.user,
                community=community,
                message=message_text,
                timestamp=now(),
            )
            return HttpResponseRedirect(
                reverse("community_detail", args=[community_id])
            )

    if not is_member and not is_pma:
        return HttpResponseForbidden(
            "You must be a member of this community to view the details."
        )

    community.tags_list = [tag.strip() for tag in community.tags.split(",")]

    events = community.events.all().order_by("date")
    events_creator = community.events.select_related("creator").all()
    current_time = now()

    upcoming_events = community.events.filter(date__gte=current_time)
    past_events = community.events.filter(date__lt=current_time).order_by(
        "-date"
    )  # Most recent past event first

    return render(
        request,
        "community/community_detail.html",
        {
            "community": community,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
            "events": events,
            "creator": events_creator,
            "members": members,
            "is_creator": is_creator,
            "is_member": is_member,
            "is_pma": is_pma,
            "messages": messages,
        },
    )


def delete_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if community.creator != request.user:
        # messages.warning(
        #     request, "You do not have permission to delete this community."
        # )
        return redirect("community_detail", community_id=community.id)

    if request.method == "POST":
        community.delete()
        # messages.success(request, "Community deleted successfully!")
        return redirect("landing")

    return redirect("community_detail", community_id=community.id)


def view_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    # Check if the logged-in user is the creator
    if community.creator != request.user:
        return redirect("community_detail", community_id=community.id)

    return render(request, "community/community_detail.html", {"community": community})


def add_member(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        try:
            user = User.objects.get(id=user_id)
            community.members.add(user)
            messages.success(request, f"{user.username} added to the community!")
        except User.DoesNotExist:
            messages.error(request, "User not found!")

    return redirect("edit_community", community_id=community.id)


def create_event(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.community = community
            event.creator = request.user
            event.save()
            messages.success(request, "Event created successfully!")
            return redirect("community_detail", community_id=community.id)
    else:
        form = EventForm()

    return render(
        request, "events/create_event.html", {"form": form, "community": community}
    )


def view_files(request, community_id):
    community = get_object_or_404(Community, id=community_id)
    allowed_file_types = ["image/jpeg", "application/pdf", "text/plain"]

    s3 = boto3.client("s3")

    is_pma_user = request.user.groups.filter(name="PMA").exists()

    if request.method == "POST":
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES["file"]
            if file.content_type not in allowed_file_types:
                messages.error(request, "Only .jpg, .pdf, and .txt files are allowed.")
            else:
                file_key = f"{community.id}/{file.name}"
                s3.upload_fileobj(file, settings.AWS_STORAGE_BUCKET_NAME, file_key)

                File.objects.create(
                    community=community,
                    title=form.cleaned_data["title"],
                    file_url=file_key,
                    description=form.cleaned_data["description"],
                    keywords=form.cleaned_data["keywords"],
                    uploader=request.user,  # Track the uploader
                )
                messages.success(request, "File uploaded successfully!")
                return HttpResponseRedirect(request.path_info)
    else:
        form = FileUploadForm()

    file_data = []
    for file in File.objects.filter(community=community).order_by("-upload_timestamp"):
        params = {"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": file.file_url}
        if file.file_url.endswith(".pdf"):
            params.update(
                {
                    "ResponseContentType": "application/pdf",
                    "ResponseContentDisposition": "inline",
                }
            )

        file_url = s3.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=86400
        )

        if file.file_url.endswith((".jpg", ".jpeg", ".png")):
            file_type = "image"
        elif file.file_url.endswith(".pdf"):
            file_type = "pdf"
        elif file.file_url.endswith(".txt"):
            file_type = "text"
        else:
            file_type = "unknown"

        file_content = None
        if file_type == "text":
            obj = s3.get_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file.file_url
            )
            file_content = obj["Body"].read().decode("utf-8")

        can_delete = is_pma_user or (file.uploader and file.uploader == request.user)

        file_data.append(
            {
                "title": file.title,
                "upload_timestamp": file.upload_timestamp,
                "description": file.description,
                "keywords": file.keyword_list(),
                "file_url": file_url,
                "file_content": file_content,
                "file_type": file_type,
                "id": file.id,
                "can_delete": can_delete,
            }
        )

    return render(
        request,
        "community/view_files.html",
        {
            "community": community,
            "form": form,
            "file_data": file_data,
        },
    )


def my_communities(request):
    # Get all the members for the logged-in user
    if not request.user.is_authenticated:
        return render(request, "login/login.html")
    members = Member.objects.filter(user=request.user)

    # Get the communities associated with those members
    communities = Community.objects.filter(members__in=members)
    for community in communities:
        community.is_member = True

        community.join_request = CommunityJoinRequest.objects.filter(
            user=request.user, community=community, status="pending"
        ).first()

    is_pma = request.user.groups.filter(name="PMA").exists()

    return render(
        request,
        "landing/landing.html",
        {"communities": communities, "is_pma": is_pma, "my_communities": True},
    )


def my_events(request):
    if not request.user.is_authenticated:
        return render(request, "login/login.html")

    user_memberships = Member.objects.filter(user=request.user)
    user_communities = Community.objects.filter(members__in=user_memberships)
    events = Event.objects.filter(community__in=user_communities).order_by("date")
    community_events = (
        Event.objects.filter(community__in=user_communities)
        .select_related("community")
        .order_by("community", "date")
    )

    rsvp_events = Event.objects.filter(
        rsvps__user=request.user, rsvps__status="attending"
    ).order_by("date")

    for event in events:
        event.is_attending = event.rsvps.filter(
            user=request.user, status="attending"
        ).exists()
        event.is_member = event.community.members.filter(user=request.user).exists()

    for community in user_communities:
        community.is_member = True  # Set membership flag
        community.join_request = CommunityJoinRequest.objects.filter(
            user=request.user, community=community, status="pending"
        ).exists()

    return render(
        request,
        "events/my_events.html",
        {
            "events": events,
            "rsvp_events": rsvp_events,
        },
    )


def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    # Check if the logged-in user is the creator of the event
    is_event_creator = request.user == event.creator

    if request.method == "POST" and "rsvp_status" in request.POST:
        status = request.POST.get("rsvp_status")
        EventRSVP.objects.update_or_create(
            event=event, user=request.user, defaults={"status": status}
        )
        messages.success(
            request, f"Your RSVP has been updated to '{status.capitalize()}'."
        )

    attending_members = event.rsvps.filter(status="attending").select_related("user")
    not_attending_members = event.rsvps.filter(status="not_attending").select_related(
        "user"
    )

    is_attending = attending_members.filter(user=request.user).exists()
    is_member = event.community.members.filter(user=request.user).exists()

    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "attending_members": attending_members,
            "not_attending_members": not_attending_members,
            "is_event_creator": is_event_creator,
        },
    )


def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.creator != request.user:
        return HttpResponseForbidden("You are not authorized to delete this event.")
    community_id = event.community.id
    event.delete()
    messages.success(request, "Event deleted successfully!")
    return redirect("community_detail", community_id=community_id)


def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if event.creator != request.user:
        return HttpResponseForbidden("You are not authorized to edit this event.")
    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully!")
            return redirect("community_detail", community_id=event.community.id)
    else:
        form = EventForm(instance=event)
    return render(request, "events/edit_event.html", {"form": form, "event": event})


def is_pma_user(user):
    return user.groups.filter(name="PMA").exists()


@login_required
@user_passes_test(is_pma_user)
def delete_file(request, file_id):
    file = get_object_or_404(File, id=file_id)

    is_pma_user = request.user.groups.filter(name="PMA").exists()
    is_uploader = file.uploader == request.user

    if is_pma_user or is_uploader:
        s3 = boto3.client("s3")
        s3.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=file.file_url.split("/")[-1],
        )

        file.delete()
        messages.success(request, "File deleted successfully.")
    else:
        messages.error(request, "You do not have permission to delete this file.")

    return redirect("view_files", community_id=file.community.id)


def create_community(request):
    form = CommunityForm()
    if request.user.groups.filter(name="PMA").exists():
        return render(request, "login/PMA.html")
    if not request.user.is_authenticated:
        return render(request, "login/login.html")

    if request.method == "POST":
        if request.user.is_authenticated:
            form = CommunityForm(request.POST, request.FILES)
            if form.is_valid():
                community = form.save(commit=False)
                community.creator = request.user

                community.save()
                Member.objects.create(user=request.user, community=community)
                return redirect("community_detail", community_id=community.id)

    return render(request, "community/create_community.html", {"form": form})


def edit_community(request, community_id):
    community = get_object_or_404(Community, id=community_id)

    # Only the creator can edit the community
    if community.creator != request.user:
        return redirect("community_detail", community_id=community.id)

    if request.method == "POST":
        form = CommunityForm(request.POST, request.FILES, instance=community)

        # Handle adding a new member
        if "add_member" in request.POST:
            member_username = request.POST.get("member_username")
            try:
                member = User.objects.get(username=member_username)
                if member not in community.members.all():
                    community.members.add(member)
                    messages.success(
                        request, f"{member.username} has been added as a member."
                    )
                else:
                    messages.warning(request, f"{member.username} is already a member.")
            except User.DoesNotExist:
                messages.error(request, "User does not exist.")

        if form.is_valid():
            community = form.save(commit=False)
            community.save()
            messages.success(request, "Community updated successfully.")
            return redirect("community_detail", community_id=community.id)
    else:
        form = CommunityForm(instance=community)

    return render(
        request,
        "community/edit_community.html",
        {
            "form": form,
            "community": community,
            "current_members": community.members.all(),
        },
    )

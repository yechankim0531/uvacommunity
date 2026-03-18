from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("my-communities/", views.my_communities, name="my_communities"),
    path("my-events/", views.my_events, name="my_events"),
    path("requests/", views.requests_page, name="requests_page"),
    path("view-files/<int:community_id>/", views.view_files, name="view_files"),
    path('login/', auth_views.LoginView.as_view(template_name='login/login.html'), name='login'),

    # Community
    path("create-community/", views.create_community, name="create_community"),
    path(
        "community/<int:community_id>/",
        views.community_detail,
        name="community_detail",
    ),
    path(
        "community/edit/<int:community_id>/",
        views.edit_community,
        name="edit_community",
    ),
    path(
        "community/delete/<int:community_id>/",
        views.delete_community,
        name="delete_community",
    ),
    path(
        "community/exit/<int:community_id>/",
        views.exit_community,
        name="exit_community",
    ),
    path(
        "community/<int:community_id>/join/",
        views.join_community,
        name="join_community",
    ),
    path(
        "community/<int:community_id>/create-event/",
        views.create_event,
        name="create_event",
    ),
    # path('login/', views.LoginView.as_view(), name='login'),

    # Event Management
    path("events/<int:event_id>/", views.event_detail, name="event_detail"),
    path("events/<int:event_id>/edit/", views.edit_event, name="edit_event"),
    path("events/<int:event_id>/delete/", views.delete_event, name="delete_event"),

    path("delete-file/<int:file_id>/", views.delete_file, name="delete_file"),

    path(
        "requests/<int:request_id>/<str:action>/",
        views.handle_join_request,
        name="handle_join_request",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

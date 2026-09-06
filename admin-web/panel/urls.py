from django.urls import path

from . import views

urlpatterns = [
    path("healthz/", views.health, name="health"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("posts/", views.post_list, name="post_list"),
    path("posts/new/", views.post_create, name="post_create"),
    path("posts/<uuid:post_id>/", views.post_edit, name="post_edit"),
    path("posts/<uuid:post_id>/preview/", views.post_preview, name="post_preview"),
    path("posts/<uuid:post_id>/trash/", views.post_trash, name="post_trash"),
    path("posts/<uuid:post_id>/revisions/<int:revision_id>/restore/", views.post_restore_revision, name="post_restore_revision"),
    path("resources/", views.resources_edit, name="resources_edit"),
    path("resources/preview/", views.resources_preview, name="resources_preview"),
    path("resources/revisions/<int:revision_id>/restore/", views.resources_restore_revision, name="resources_restore_revision"),
    path("files/", views.files, name="files"),
    path("files/download/", views.file_download, name="file_download"),
    path("uploads/", views.upload_create, name="upload_create"),
    path("uploads/<uuid:upload_id>/", views.upload_status, name="upload_status"),
    path("uploads/<uuid:upload_id>/chunks/<int:index>/", views.upload_chunk, name="upload_chunk"),
    path("uploads/<uuid:upload_id>/complete/", views.upload_complete, name="upload_complete"),
    path("uploads/<uuid:upload_id>/cancel/", views.upload_cancel, name="upload_cancel"),
    path("media/upload/", views.media_upload, name="media_upload"),
    path("media/", views.media_library, name="media_library"),
    path("media/trash/", views.media_trash, name="media_trash"),
    path("trash/", views.trash, name="trash"),
    path("trash/<uuid:item_id>/restore/", views.trash_restore, name="trash_restore"),
    path("trash/<uuid:item_id>/delete/", views.trash_delete, name="trash_delete"),
]

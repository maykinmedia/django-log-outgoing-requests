from django.urls import path

from .views import OriginalResponseBodyView, PrettifyResponseBodyView

urlpatterns = [
    path(
        "prettify/",
        PrettifyResponseBodyView.as_view(),
        name="prettify_view",
    ),
    path(
        "original/",
        OriginalResponseBodyView.as_view(),
        name="original_view",
    ),
]

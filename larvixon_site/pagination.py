from rest_framework.pagination import PageNumberPagination
from django.conf import settings


class ForceHTTPSPaginator(PageNumberPagination):
    """
    Custom paginator that forces HTTPS in next and previous URLs
    if the FORCE_HTTPS setting is enabled.
    """

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)

        if settings.FORCE_HTTPS:
            if response.data["next"]:
                response.data["next"] = response.data["next"].replace(
                    "http://", "https://"
                )

            if response.data["previous"]:
                response.data["previous"] = response.data["previous"].replace(
                    "http://", "https://"
                )

        return response

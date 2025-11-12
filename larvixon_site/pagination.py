from rest_framework.pagination import PageNumberPagination
from django.conf import settings
import sys


class ForceHTTPSPaginator(PageNumberPagination):

    def get_paginated_response(self, data):

        # --- START OF DIAGNOSTICS ---
        print("--- DEBUG: ForceHTTPSPaginator Run ---", file=sys.stderr)

        if settings.FORCE_HTTPS:
            print(
                "--- DEBUG: settings.FORCE_HTTPS is True. Starting replacement...",
                file=sys.stderr,
            )
        else:
            print(
                "--- DEBUG: settings.FORCE_HTTPS is FALSE. Skipping replacement. ---",
                file=sys.stderr,
            )
        # --- END OF DIAGNOSTICS ---

        response = super().get_paginated_response(data)

        if settings.FORCE_HTTPS:
            if response.data["next"]:
                print(
                    f"--- DEBUG: Original 'next': {response.data['next']}",
                    file=sys.stderr,
                )
                response.data["next"] = response.data["next"].replace(
                    "http://", "https://"
                )
                print(
                    f"--- DEBUG: Corrected 'next': {response.data['next']}",
                    file=sys.stderr,
                )

            if response.data["previous"]:
                print(
                    f"--- DEBUG: Original 'previous': {response.data['previous']}",
                    file=sys.stderr,
                )
                response.data["previous"] = response.data["previous"].replace(
                    "http://", "https://"
                )
                print(
                    f"--- DEBUG: Corrected 'previous': {response.data['previous']}",
                    file=sys.stderr,
                )

        return response

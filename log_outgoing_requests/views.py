import json

from django.http import JsonResponse
from django.views import View


class PrettifyResponseBodyView(View):
    def post(self, request):
        received_data = json.loads(request.body)
        return JsonResponse({"newValue": "Toggled to pretty"})


class OriginalResponseBodyView(View):
    def post(self, request):
        received_data = json.loads(request.body)
        return JsonResponse({"newValue": "Toggled to original"})

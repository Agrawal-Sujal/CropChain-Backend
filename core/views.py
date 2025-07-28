from django.http import JsonResponse
from .get_pending_images import get_pending_images


def show_pending_images(request):
    if request.method == "GET":
        try:
            pending_urls = get_pending_images()
            return JsonResponse({"pending_urls": pending_urls})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Only GET method allowed."}, status=405)

from django.conf import settings


def environment_callback(request):
    if settings.DEBUG:
        return ("Development", "warning")
    return ("Production", "success")

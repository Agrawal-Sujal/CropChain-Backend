from django.contrib import admin
from .models import FCMToken

# Register your models here.
@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'token', 'aadhaar_number', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('device_id', 'token', 'aadhaar_number')
    readonly_fields = ('created_at', 'updated_at')

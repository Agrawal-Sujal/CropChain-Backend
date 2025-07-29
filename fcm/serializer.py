from rest_framework import serializers
from .models import FCMToken

class FCMTokenSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=255)
    aadhaar_number = serializers.CharField(max_length=12)
    
    def create(self, validated_data):
        device_id = validated_data.get('device_id')
        token = validated_data.get('token')
        aadhaar_number = validated_data.get('aadhaar_number')
        
        # Use update_or_create to handle both create and update cases
        fcm_token, created = FCMToken.objects.update_or_create(
            device_id=device_id,
            defaults={
                'token': token,
                'aadhaar_number': aadhaar_number
            }
        )
        return fcm_token
    


class NotificationSerializer(serializers.Serializer):
    aadhar_id = serializers.CharField(max_length=12)

    def validate_aadhar_id(self, value):
        if not value.isdigit() or len(value) != 12:
            raise serializers.ValidationError("Aadhar must be exactly 12 digits")
        return value

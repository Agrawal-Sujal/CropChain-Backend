from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FCMToken
from .serializer import FCMTokenSerializer
import logging
from rest_framework.decorators import api_view
from .serializer import NotificationSerializer
from .send_notification import sendNotifications
from asgiref.sync import async_to_sync

# Get a logger for this module
logger = logging.getLogger(__name__)

class RegisterFCMToken(APIView):
    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        if serializer.is_valid():
            device_id = serializer.validated_data['device_id']
            token = serializer.validated_data['token']
            aadhaar_number = serializer.validated_data['aadhaar_number']
            
            logger.info(f"Processing FCM token registration:")
            logger.info(f"  Device ID: {device_id}")
            logger.info(f"  Token: {token}")
            logger.info(f"  Aadhaar Number: {aadhaar_number}")
            
            # Check if device_id already exists
            existing_token = FCMToken.objects.filter(device_id=device_id).first()
            
            if existing_token:
                logger.info(f"  Updating existing token for device_id: {device_id}")
                message = "Token updated successfully."
            else:
                logger.info(f"  Creating new token for device_id: {device_id}")
                message = "Token registered successfully."
            
            # Let the serializer handle the create/update logic
            fcm_token = serializer.save()
            logger.info(f"  Operation completed successfully. Updated at: {fcm_token.updated_at}")

            return Response({"message": message}, status=status.HTTP_201_CREATED)
        
        logger.error(f"Invalid serializer data: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
def sendNotification(request):
    serializer = NotificationSerializer(data=request.data)
    if serializer.is_valid():
        # don’t save, just return
        aadhar_id = serializer.validated_data["aadhar_id"]
        title = serializer.validated_data["title"]
        body = serializer.validated_data["body"]
        imageId = serializer.validated_data["imageId"]
        imageType = serializer.validated_data["imageType"]
        async_to_sync(sendNotifications)(aadharId=aadhar_id,title = title, body = body,imageId = imageId,imageType = imageType)

        return Response({
            "message": "Aadhar received",
            "aadhar_id": serializer.validated_data["aadhar_id"]
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
import logging
import os
from .models import FCMToken
import firebase_admin
from firebase_admin import credentials, messaging
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from CropChain.settings import BASE_DIR
import json

load_dotenv(os.path.join(BASE_DIR, '.env'))


# Configure logging for this module
logger = logging.getLogger(__name__)

# Your contract address
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
FCM_CRED = os.getenv('FCM_CRED')
# Initialize Firebase Admin SDK (do this once at module level)
try:
    fcm_cred = json.loads(FCM_CRED)
    cred = credentials.Certificate(fcm_cred)
    firebase_admin.initialize_app(cred)
    logger.info("Fibase Admin SDK initialized successfully")
except ValueError:
    # App already initialized
    logger.info("Firebase Admin SDK already initialized")
    pass
except FileNotFoundError:
    logger.warning("Firebase notifications will not work without the service account key file.")
    pass

async def sendNotifications(aadharId, title="Sujal's Notification", body="Kaise ho sab log?", data=None):
    """Send FCM notification to user with proper logging"""
    try:
        
        # Get all FCM tokens for the given aadhar ID - use sync_to_async for database operations
        logger.info(f"Searching for FCM tokens for Aadhar ID: {aadharId}")
        fcm_tokens = await sync_to_async(FCMToken.objects.filter)(aadhaar_number=str(aadharId))
        tokens = await sync_to_async(lambda: [token.token for token in fcm_tokens])()
        
        # If no tokens found, return early
        if not tokens:
            logger.warning(f"No FCM tokens found for aadhar ID: {aadharId}")
            return False
        
        logger.info(f"Found {len(tokens)} FCM tokens for user")
        
        # Prepare notification data
        if data is None:
            data = {}
        
        # Create the multicast message
        logger.info("Creating notification message...")
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data,
            tokens=tokens,
        )
        
        # Send the notification
        logger.info("Sending notification to Firebase...")
        response = messaging.send_each_for_multicast(message)
        
        # Handle failures
        if response.failure_count > 0:
            responses = response.responses
            failed_tokens = []
            for idx, resp in enumerate(responses):
                if not resp.success:
                    # The order of responses corresponds to the order of the registration tokens.
                    failed_tokens.append(tokens[idx])
            logger.warning(f"List of tokens that caused failures: {failed_tokens}")
            
            # Optionally remove failed tokens from database - use sync_to_async
            logger.info("Cleaning up failed tokens from database...")
            for failed_token in failed_tokens:
                await sync_to_async(FCMToken.objects.filter(token=failed_token).delete)()
            logger.info(f"Removed {len(failed_tokens)} failed tokens from database")
        
        logger.info(f"Successfully sent messages: {response.success_count}")
        logger.info(f"Failed to send messages: {response.failure_count}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}", exc_info=True)
        return False


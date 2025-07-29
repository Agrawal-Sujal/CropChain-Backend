import logging
import os
from pathlib import Path
from web3 import Web3
from fcm.models import FCMToken
import firebase_admin
from firebase_admin import credentials, messaging
from asgiref.sync import sync_to_async
from dotenv import load_dotenv
from CropChain.settings import BASE_DIR

load_dotenv(os.path.join(BASE_DIR, '.env'))


# Configure logging for this module
logger = logging.getLogger(__name__)

# Your contract address
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
abi = [{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"_user","type":"address"},{"indexed":False,"internalType":"string","name":"imageUrl","type":"string"}],"name":"ImageSubmitted","type":"event"},{"inputs":[{"internalType":"string","name":"_url","type":"string"},{"internalType":"string","name":"_solution","type":"string"}],"name":"AI_solution","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_farmer","type":"address"},{"internalType":"uint256","name":"_adhar_id","type":"uint256"}],"name":"add_farmer","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_scientist","type":"address"},{"internalType":"uint256","name":"_adhar_id","type":"uint256"},{"internalType":"uint256","name":"_scientist_id","type":"uint256"}],"name":"add_scientist","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"farmer_map","outputs":[{"internalType":"uint256","name":"level","type":"uint256"},{"internalType":"uint256","name":"adhar_id","type":"uint256"},{"internalType":"uint256","name":"auth_points","type":"uint256"},{"internalType":"string","name":"images_upload","type":"string"},{"internalType":"string","name":"image_VR","type":"string"},{"internalType":"address","name":"farmer_add","type":"address"},{"internalType":"uint256","name":"correctReportCount","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"getKvkManager","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"get_close_images","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"get_farmers","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"get_open_images","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"get_pending_images","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"get_scientists","outputs":[{"internalType":"address[]","name":"","type":"address[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"","type":"string"}],"name":"image_verifiers","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"","type":"string"}],"name":"images","outputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"string","name":"imageUrl","type":"string"},{"internalType":"string","name":"AI_sol","type":"string"},{"internalType":"address","name":"reviewer","type":"address"},{"internalType":"string","name":"reviewer_sol","type":"string"},{"internalType":"bool","name":"got_AI","type":"bool"},{"internalType":"bool","name":"reviewed","type":"bool"},{"internalType":"bool","name":"verified","type":"bool"},{"internalType":"uint256","name":"verificationCount","type":"uint256"},{"internalType":"uint256","name":"true_count","type":"uint256"},{"internalType":"uint256","name":"false_count","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"_url","type":"string"},{"internalType":"string","name":"_solution","type":"string"}],"name":"review_image","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"scientist_map","outputs":[{"internalType":"uint256","name":"level","type":"uint256"},{"internalType":"uint256","name":"adhar_id","type":"uint256"},{"internalType":"uint256","name":"auth_points","type":"uint256"},{"internalType":"uint256","name":"scientist_id","type":"uint256"},{"internalType":"string","name":"image_VR","type":"string"},{"internalType":"string","name":"image_rvd","type":"string"},{"internalType":"address","name":"scientist_add","type":"address"},{"internalType":"uint256","name":"correctReportCount","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_user","type":"address"},{"internalType":"string","name":"_url","type":"string"}],"name":"upload_image","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"verifiers_map","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"string","name":"_url","type":"string"},{"internalType":"bool","name":"_choice","type":"bool"}],"name":"verify_image","outputs":[],"stateMutability":"nonpayable","type":"function"}]

# Initialize Firebase Admin SDK (do this once at module level)
try:
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    fcm_json_path = os.path.join(project_root, 'fcm.json')
    
    cred = credentials.Certificate(fcm_json_path)
    firebase_admin.initialize_app(cred)
    logger.info("Fibase Admin SDK initialized successfully")
except ValueError:
    # App already initialized
    logger.info("Firebase Admin SDK already initialized")
    pass
except FileNotFoundError:
    logger.warning(f"Warning: fcm.json not found at {fcm_json_path}")
    logger.warning("Firebase notifications will not work without the service account key file.")
    pass

async def sendNotification(user, title="Sujal's Notification", body="Kaise ho sab log?", data=None):
    """Send FCM notification to user with proper logging"""
    try:
        logger.info(f"Starting notification process for user: {user}")
        
        # Initialize Web3 connection
        w3 = Web3(Web3.HTTPProvider(os.getenv('HTTP_PROVIDER_1')))
        
        if not w3.is_connected():
            logger.error("Failed to connect to Ethereum network")
            return False
            
        logger.info("Connected to Ethereum network")
        
        # Get contract instance
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
        logger.info(f"Contract loaded at address: {CONTRACT_ADDRESS}")
        
        # Get farmer info from blockchain
        logger.info("Fetching farmer information from blockchain...")
        farmer_info = contract.functions.farmer_map(user).call()
        aadharId = farmer_info[1]
        logger.info(f"Farmer Aadhar ID: {aadharId}")
        
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


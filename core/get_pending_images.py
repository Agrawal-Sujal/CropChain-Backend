import logging
import os
from web3 import Web3
from dotenv import load_dotenv
from CropChain.settings import BASE_DIR

load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configure logging for this module
logger = logging.getLogger(__name__)

abi = os.getenv('ABI')
w3 = Web3(Web3.HTTPProvider(os.getenv('HTTP_PROVIDER_1')))

def get_pending_images():
    """Get pending images from blockchain with proper logging"""
    try:
        logger.info("Fetching pending images from blockchain...")
        
        # Check Web3 connection
        if not w3.is_connected():
            logger.error("Failed to connect to Ethereum network")
            return []
            
        logger.info("Connected to Ethereum network")
        
        # Get contract instance
        contract = w3.eth.contract(address= os.getenv('CONTRACT_ADDRESS'), abi=abi)
        logger.info("Contract loaded successfully")
        
        # Call the contract function
        logger.info("Calling get_pending_images() on contract...")
        urls = contract.functions.get_pending_images().call()
        
        if urls:
            url_list = urls.split("$$$")
            logger.info(f"Found {len(url_list)} pending images")
            logger.debug(f"Pending images: {url_list}")
            return url_list
        else:
            logger.info("No pending images found")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching pending images: {e}", exc_info=True)
        return []

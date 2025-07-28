import time
import asyncio
import logging
import os
from pathlib import Path
from .run_ai_on_images import run_ai_on_image
from .upload_result import uploadResult
from web3 import AsyncWeb3, WebSocketProvider, HTTPProvider
from web3.utils.subscriptions import LogsSubscription, LogsSubscriptionContext
from web3._utils.events import get_event_data
from .send_notification import sendNotification
from dotenv import load_dotenv
from CropChain.settings import BASE_DIR

load_dotenv(os.path.join(BASE_DIR, '.env'))


# Configure logging for this module
logger = logging.getLogger(__name__)

# Your contract address
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')

# Provider configurations
PROVIDERS = {
    "wss_provider_1": os.getenv('WSS_PROVIDER_1'),
    "wss_provider_2":os.getenv('WSS_PROVIDER_2'),
}

async def test_provider(provider_url, is_websocket=True):
    """Test if a provider is working"""
    try:
        if is_websocket:
            w3 = await AsyncWeb3(WebSocketProvider(provider_url))
        else:
            w3 = AsyncWeb3(HTTPProvider(provider_url))
        
        # Test basic connectivity
        block_number = await w3.eth.block_number
        logger.info(f"Provider {provider_url} is working. Latest block: {block_number}")
        return True
    except Exception as e:
        logger.error(f"Provider {provider_url} failed: {e}")
        return False

async def log_handler(handler_context: LogsSubscriptionContext) -> None:
    try:
        log = handler_context.result
        event_abi = {
        "anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"_user","type":"address"},{"indexed":False,"internalType":"string","name":"imageUrl","type":"string"}],"name":"ImageSubmitted","type":"event"
        }
        w3 = handler_context.async_w3
        decoded = get_event_data(w3.codec, event_abi, log)
        urls = decoded["args"]["imageUrl"].split("$$$")
        logger.info("New ImageSubmitted Event:")
        logger.info(f"User: {decoded['args']['_user']}")
        logger.info(f"URL: {decoded['args']['imageUrl']}")
        logger.info(f"Transaction Hash: {log['transactionHash'].hex() if hasattr(log['transactionHash'], 'hex') else log['transactionHash']}")
        user = decoded["args"]["_user"]
        for url in urls:
            logger.info(f"Running AI on image: {url}")
            result = run_ai_on_image(url)
            logger.info(f"AI Result: {result}")
            uploadResult(url,result)
            await sendNotification(user)
    except Exception as e:
        logger.error(f"Error in log_handler: {e}", exc_info=True)


async def sub_manager():
    max_retries = 5
    retry_delay = 10  # seconds
    
    # Try different providers
    working_provider = None
    
    # Test WebSocket providers first
    for provider_name, provider_url in PROVIDERS.items():
        if "ws" in provider_name:
            logger.info(f"Testing {provider_name}: {provider_url}")
            if await test_provider(provider_url, is_websocket=True):
                working_provider = provider_url
                break
    
    if not working_provider:
        logger.warning("No WebSocket providers working. Trying HTTP providers...")
        for provider_name, provider_url in PROVIDERS.items():
            if "http" in provider_name and "ws" not in provider_name:
                logger.info(f"Testing {provider_name}: {provider_url}")
                if await test_provider(provider_url, is_websocket=False):
                    working_provider = provider_url
                    break
    
    if not working_provider:
        logger.error("No working providers found. Please check your API keys and network connection.")
        raise Exception("No working providers found. Please check your API keys and network connection.")
    
    logger.info(f"Using provider: {working_provider}")
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to connect (attempt {attempt + 1}/{max_retries})")
            
            # Connect to provider
            if "ws" in working_provider:
                w3 = await AsyncWeb3(WebSocketProvider(working_provider))
            else:
                w3 = await AsyncWeb3(HTTPProvider(working_provider))
            
            logger.info("Successfully connected")
            
            # Only subscribe to WebSocket events if using WebSocket provider
            if "ws" in working_provider:
                await w3.subscription_manager.subscribe([
                    LogsSubscription(
                        label="ImageSubmitted (address _user, string imageUrl)",
                        address=w3.to_checksum_address(CONTRACT_ADDRESS),
                        topics=[["0x2176ff554abc6afb8a3baf0448d7ff22c25829c4aee3806c623ed36edb2b2bba"]],
                        handler=log_handler,
                    )
                ])

                logger.info("Subscribed to blockchain events. Waiting for ImageSubmitted events...")
                await w3.subscription_manager.handle_subscriptions()
            else:
                logger.warning("Using HTTP provider - real-time events not available")
                logger.info("Consider setting up WebSocket provider for real-time event listening")
                # You could implement polling here instead
                await asyncio.sleep(60)  # Sleep for 1 minute
                
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Max retries exceeded. Please check your network connection and API key.")
                raise


def start():
    try:
        logger.info("Starting blockchain event listener...")
        asyncio.run(sub_manager())
    except KeyboardInterrupt:
        logger.info("Background worker stopped by user")
    except Exception as e:
        logger.error(f"Background worker failed: {e}", exc_info=True)
    
    

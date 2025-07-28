import asyncio
import logging
import signal
from typing import Optional
from .run_ai_on_images import run_ai_on_image
from .upload_result import uploadResult
from web3 import AsyncWeb3, WebSocketProvider, HTTPProvider
from web3.utils.subscriptions import LogsSubscription, LogsSubscriptionContext
from web3._utils.events import get_event_data
from .send_notification import sendNotification
import os
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

# Global variables for graceful shutdown
shutdown_event = asyncio.Event()
w3_instance: Optional[AsyncWeb3] = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("Received shutdown signal, initiating graceful shutdown...")
    shutdown_event.set()

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def test_provider(provider_url, is_websocket=True):
    """Test if a provider is working with timeout"""
    try:
        if is_websocket:
            # Add timeout for WebSocket connections
            w3 = await asyncio.wait_for(
                AsyncWeb3(WebSocketProvider(provider_url)),
                timeout=30.0
            )
        else:
            w3 = AsyncWeb3(HTTPProvider(provider_url))
        
        # Test basic connectivity with timeout
        block_number = await asyncio.wait_for(
            w3.eth.block_number,
            timeout=10.0
        )
        logger.info(f"Provider {provider_url} is working. Latest block: {block_number}")
        return True
    except asyncio.TimeoutError:
        logger.error(f"Provider {provider_url} timed out")
        return False
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
        logger.info(f"user: {decoded['args']['_user']}")
        logger.info(f"url: {decoded['args']['imageUrl']}")
        logger.info(f"transactionHash: {log['transactionHash'].hex() if hasattr(log['transactionHash'], 'hex') else log['transactionHash']}")
        user = decoded["args"]["_user"]
        for url in urls:
            logger.info(f"Running AI on image: {url}")
            result = run_ai_on_image(url)
            logger.info(f"AI result: {result}")
            uploadResult(url, result)
            await sendNotification(user)
    except Exception as e:
        logger.error(f"Error in log_handler: {e}", exc_info=True)

async def health_check(w3: AsyncWeb3, provider_url: str) -> bool:
    """Periodic health check to ensure connection is still alive"""
    try:
        # Try to get the latest block number with timeout
        block_number = await asyncio.wait_for(
            w3.eth.block_number,
            timeout=10.0
        )
        logger.debug(f"Health check passed - Latest block: {block_number}")
        return True
    except asyncio.TimeoutError:
        logger.warning(f"Health check timed out for {provider_url}")
        return False
    except Exception as e:
        logger.warning(f"Health check failed for {provider_url}: {e}")
        return False

async def connection_monitor(w3: AsyncWeb3, provider_url: str):
    """Monitor connection health and reconnect if needed"""
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(30)  # Check every 30 seconds
            if not await health_check(w3, provider_url):
                logger.warning("Connection health check failed, triggering reconnection...")
                shutdown_event.set()  # This will trigger reconnection in main loop
                break
        except Exception as e:
            logger.error(f"Error in connection monitor: {e}")
            break

async def find_working_provider():
    """Find a working provider with infinite retries"""
    while not shutdown_event.is_set():
        # Test WebSocket providers first
        for provider_name, provider_url in PROVIDERS.items():
            if "ws" in provider_name:
                logger.info(f"Testing {provider_name}: {provider_url}")
                if await test_provider(provider_url, is_websocket=True):
                    return provider_url
        
        logger.warning("No WebSocket providers working. Trying HTTP providers...")
        for provider_name, provider_url in PROVIDERS.items():
            if "http" in provider_name and "ws" not in provider_name:
                logger.info(f"Testing {provider_name}: {provider_url}")
                if await test_provider(provider_url, is_websocket=False):
                    return provider_url
        
        logger.error("No working providers found. Retrying in 60 seconds...")
        await asyncio.sleep(60)

async def sub_manager():
    """Main subscription manager with infinite retry logic and better error handling"""
    global w3_instance
    
    while not shutdown_event.is_set():
        try:
            # Find working provider
            working_provider = await find_working_provider()
            if shutdown_event.is_set():
                break
                
            logger.info(f"Using provider: {working_provider}")
            
            # Connect to provider with timeout
            try:
                if "ws" in working_provider:
                    w3_instance = await asyncio.wait_for(
                        AsyncWeb3(WebSocketProvider(working_provider)),
                        timeout=30.0
                    )
                else:
                    w3_instance = AsyncWeb3(HTTPProvider(working_provider))
                
                logger.info("Successfully connected")
            except asyncio.TimeoutError:
                logger.error("Connection timeout, trying next provider...")
                continue
            except Exception as e:
                logger.error(f"Connection failed: {e}")
                continue
            
            # Start connection monitor
            monitor_task = None
            if "ws" in working_provider:
                monitor_task = asyncio.create_task(connection_monitor(w3_instance, working_provider))
            
            # Only subscribe to WebSocket events if using WebSocket provider
            if "ws" in working_provider:
                try:
                    await w3_instance.subscription_manager.subscribe([
                        LogsSubscription(
                            label="ImageSubmitted (address _user, string imageUrl)",
                            address=w3_instance.to_checksum_address(CONTRACT_ADDRESS),
                            topics=[["0x2176ff554abc6afb8a3baf0448d7ff22c25829c4aee3806c623ed36edb2b2bba"]],
                            handler=log_handler,
                        )
                    ])

                    logger.info("Subscribed to blockchain events. Waiting for ImageSubmitted events...")
                    
                    # Wait for either shutdown or subscription to end with timeout handling
                    try:
                        await asyncio.wait_for(
                            w3_instance.subscription_manager.handle_subscriptions(),
                            timeout=None  # No timeout - wait indefinitely
                        )
                    except asyncio.TimeoutError:
                        logger.info("Subscription timeout, reconnecting...")
                    except Exception as e:
                        logger.error(f"Subscription error: {e}")
                        if "semaphore timeout" in str(e).lower() or "winerror 121" in str(e).lower():
                            logger.warning("Windows semaphore timeout detected, switching to HTTP provider...")
                            # Force switch to HTTP provider
                            shutdown_event.set()
                            break
                except Exception as e:
                    logger.error(f"Subscription setup failed: {e}")
                    if "semaphore timeout" in str(e).lower() or "winerror 121" in str(e).lower():
                        logger.warning("Windows semaphore timeout detected, switching to HTTP provider...")
                        shutdown_event.set()
                        break
            else:
                logger.warning("Using HTTP provider - real-time events not available")
                logger.info("Consider setting up WebSocket provider for real-time event listening")
                # Implement polling here instead
                while not shutdown_event.is_set():
                    await asyncio.sleep(60)  # Sleep for 1 minute
                    
        except Exception as e:
            logger.error(f"Connection error: {e}", exc_info=True)
            if not shutdown_event.is_set():
                logger.info("Retrying in 30 seconds...")
                await asyncio.sleep(30)
        finally:
            # Cleanup
            if monitor_task:
                monitor_task.cancel()
            if w3_instance:
                try:
                    await w3_instance.provider.disconnect()
                except:
                    pass
                w3_instance = None

async def graceful_shutdown():
    """Gracefully shutdown the application"""
    logger.info("Starting graceful shutdown...")
    shutdown_event.set()
    
    if w3_instance:
        try:
            await w3_instance.provider.disconnect()
            logger.info("Web3 connection closed")
        except Exception as e:
            logger.error(f"Error closing Web3 connection: {e}")
    
    logger.info("Graceful shutdown completed")

def start():
    """Start the blockchain event listener with improved long-term reliability"""
    try:
        logger.info("Starting blockchain event listener...")
        asyncio.run(sub_manager())
    except KeyboardInterrupt:
        logger.info("Background worker stopped by user")
    except Exception as e:
        logger.error(f"Background worker failed: {e}", exc_info=True)
    finally:
        # Ensure graceful shutdown
        try:
            asyncio.run(graceful_shutdown())
        except:
            pass 
import logging
import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv
from CropChain.settings import BASE_DIR

load_dotenv(os.path.join(BASE_DIR, '.env'))

# Configure logging for this module
logger = logging.getLogger(__name__)

abi = os.getenv('ABI')
pk = os.getenv('PRIVATE_KEY')
address = os.getenv('ADDRESS')
contractAddress = os.getenv('CONTRACT_ADDRESS')

def uploadResult(url, result):
    """Upload AI result to blockchain with proper logging"""
    try:
        logger.info(f"Starting blockchain upload for URL: {url}")
        logger.info(f"AI Result: {result}")
        
        # Initialize Web3 connection
        w3 = Web3(Web3.HTTPProvider(os.getenv('HTTP_PROVIDER_1')))
        
        # Check connection
        if not w3.is_connected():
            logger.error("Failed to connect to Ethereum network")
            return False
            
        logger.info("Connected to Ethereum network")
        
        # Reference the deployed contract
        billboard = w3.eth.contract(address=contractAddress, abi=abi)
        logger.info(f"Contract loaded at address: {contractAddress}")

        # Get current nonce
        nonce = w3.eth.get_transaction_count(address)
        logger.info(f"Current nonce: {nonce}")

        # Manually build and sign a transaction
        logger.info("Building transaction...")
        unsent_billboard_tx = billboard.functions.AI_solution(url, result).build_transaction({
            "from": address,
            "nonce": nonce,
        })
        
        logger.info("Signing transaction...")
        signed_tx = w3.eth.account.sign_transaction(unsent_billboard_tx, private_key=pk)
        logger.info("Transaction signed successfully")

        # Send the raw transaction
        logger.info("Sending transaction to blockchain...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = '0x' + tx_hash.hex()
        logger.info(f"Transaction hash: {tx_hash_hex}")
        
        # Wait for transaction receipt
        logger.info("Waiting for transaction confirmation...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt.status == 1:
            logger.info("Transaction confirmed successfully!")
            logger.info(f"Gas used: {tx_receipt.gasUsed}")
            logger.info(f"Block number: {tx_receipt.blockNumber}")
            return True
        else:
            logger.error("Transaction failed")
            return False
            
    except Exception as e:
        logger.error(f"Error uploading result to blockchain: {e}", exc_info=True)
        return False

import backoff
import logging
import os
import pandas as pd
import time
import requests
import uuid
import yaml
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List, Union, Tuple
from utils.token_minter import TokenMinter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Load config/environment variables
config_file_path = "config.yaml"
with open(config_file_path, 'r') as config_file:
    CONFIG_DATA = yaml.safe_load(config_file)
    DATABRICKS_HOST = CONFIG_DATA['databricks']['host']
    SPACE_ID = CONFIG_DATA['databricks']['genie']['space_id']

CLIENT_ID = os.environ.get("DATABRICKS_CLIENT_ID")
CLIENT_SECRET = os.environ.get("DATABRICKS_CLIENT_SECRET")

try:
    token_minter = TokenMinter(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        host=DATABRICKS_HOST
    )
except Exception as e:
    logger.error(f"Failed to initialize TokenMinter: {e}")
    token_minter = None

class GenieClient:
    def __init__(self, host: str, space_id: str, token_minter: TokenMinter):
        self.host = host
        self.space_id = space_id

        if token_minter is None:
            raise ValueError("GenieClient: TokenMinter passed in is None.")
        self.token_minter = token_minter
        self.update_headers()
        
        self.base_url = f"https://{host}/api/2.0/genie/spaces/{space_id}"
    
    def update_headers(self) -> None:
        """Update headers with fresh token from token_minter"""
        self.headers = {
            "Authorization": f"Bearer {self.token_minter.get_token()}",
            "Content-Type": "application/json"
        }
    
    @backoff.on_exception(
        backoff.expo,
        Exception,  
        max_tries=5,
        factor=2,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            f"API request failed. Retrying in {details['wait']:.2f} seconds (attempt {details['tries']})"
        )
    )
    def start_conversation(self, question: str) -> Dict[str, Any]:
        """Start a new conversation with the given question"""
        self.update_headers()  # Refresh token before API call
        url = f"{self.base_url}/start-conversation"
        payload = {"content": question}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()
    
    @backoff.on_exception(
        backoff.expo,
        Exception,  # Retry on any exception
        max_tries=5,
        factor=2,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            f"API request failed. Retrying in {details['wait']:.2f} seconds (attempt {details['tries']})"
        )
    )
    def send_message(self, conversation_id: str, message: str) -> Dict[str, Any]:
        """Send a follow-up message to an existing conversation"""
        self.update_headers()  # Refresh token before API call
        url = f"{self.base_url}/conversations/{conversation_id}/messages"
        payload = {"content": message}
        
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    @backoff.on_exception(
        backoff.expo,
        Exception,  # Retry on any exception
        max_tries=5,
        factor=2,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            f"API request failed. Retrying in {details['wait']:.2f} seconds (attempt {details['tries']})"
        )
    )
    def get_message(self, conversation_id: str, message_id: str) -> Dict[str, Any]:
        """Get the details of a specific message"""
        self.update_headers()  # Refresh token before API call
        url = f"{self.base_url}/conversations/{conversation_id}/messages/{message_id}"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    @backoff.on_exception(
        backoff.expo,
        Exception,  # Retry on any exception
        max_tries=5,
        factor=2,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            f"API request failed. Retrying in {details['wait']:.2f} seconds (attempt {details['tries']})"
        )
    )
    def get_query_result(self, conversation_id: str, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Get the query result using the attachment_id endpoint"""
        self.update_headers()  # Refresh token before API call
        url = f"{self.base_url}/conversations/{conversation_id}/messages/{message_id}/attachments/{attachment_id}/query-result"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        result = response.json()
        
        # Extract data_array from the correct nested location
        data_array = []
        if 'statement_response' in result:
            if 'result' in result['statement_response']:
                data_array = result['statement_response']['result'].get('data_array', [])
            
        return {
                    'data_array': data_array,
                    'schema': result.get('statement_response', {}).get('manifest', {}).get('schema', {})
                }

    @backoff.on_exception(
        backoff.expo,
        Exception,  # Retry on any exception
        max_tries=5,
        factor=2,
        jitter=backoff.full_jitter,
        on_backoff=lambda details: logger.warning(
            f"API request failed. Retrying in {details['wait']:.2f} seconds (attempt {details['tries']})"
        )
    )
    def execute_query(self, conversation_id: str, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """Execute a query using the attachment_id endpoint"""
        self.update_headers()  # Refresh token before API call
        url = f"{self.base_url}/conversations/{conversation_id}/messages/{message_id}/attachments/{attachment_id}/execute-query"
        
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    

    def wait_for_message_completion(self, conversation_id: str, message_id: str, timeout: int = 300, poll_interval: int = 2) -> Dict[str, Any]:
        """
        Wait for a message to reach a terminal state (COMPLETED, ERROR, etc.).
        
        Args:
            conversation_id: The ID of the conversation
            message_id: The ID of the message
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds
            
        Returns:
            The completed message
        """
        
        start_time = time.time()
        attempt = 1
        
        while time.time() - start_time < timeout:
            
            message = self.get_message(conversation_id, message_id)
            status = message.get("status")
            
            if status in ["COMPLETED", "ERROR", "FAILED"]:
                logger.info("Full Genie message: %s", message)
                return message
                
            time.sleep(poll_interval)
            attempt += 1
            
        raise TimeoutError(f"Message processing timed out after {timeout} seconds")

def start_new_conversation(question: str) -> Tuple[str, str, Optional[pd.DataFrame], Optional[str]]:
    """
    Start a new conversation with Genie.
    
    Args:
        question: The initial question
        
    Returns:
        Tuple containing:
        - conversation_id: The new conversation ID
        - text_response: Either from a Genie text response or a query description
        - dataframe_response: DataFrame response if applicable, otherwise None
        - query_text: SQL query text if applicable, otherwise None
    """
        
    try:
        client = GenieClient(
            host=DATABRICKS_HOST,
            space_id=SPACE_ID,
            token_minter=token_minter
        )

        # Start a new conversation
        response = client.start_conversation(question)
        conversation_id = response.get("conversation_id")
        message_id = response.get("message_id")
        
        # Wait for the message to complete
        complete_message = client.wait_for_message_completion(conversation_id, message_id)
        
        # Process the response
        text_response, df_response, query_text = process_genie_response(client, conversation_id, message_id, complete_message)

        logger.info(f"Started a new conversation with id: {conversation_id}")
        return conversation_id, text_response, df_response, query_text
        
    except Exception as e:
        return None, f"Sorry, an error occurred: {str(e)}. Please try again.", None, None

def continue_conversation(conversation_id: str, question: str) -> Tuple[str, Optional[pd.DataFrame], Optional[str]]:
    """
    Send a follow-up message in an existing conversation.
    
    Args:
        conversation_id: The existing conversation ID
        question: The follow-up question
        
    Returns:
        Tuple containing:
        - text_response: Either from a Genie text response or a query description
        - dataframe_response: DataFrame response if applicable, otherwise None
        - query_text: SQL query text if applicable, otherwise None
    """
    logger.info(f"Continuing conversation {conversation_id} with question: {question}")
        
    try:
        client = GenieClient(
            host=DATABRICKS_HOST,
            space_id=SPACE_ID,
            token_minter=token_minter
        )

        # Send follow-up message in existing conversation
        response = client.send_message(conversation_id, question)
        message_id = response.get("message_id")
        
        # Wait for the message to complete
        complete_message = client.wait_for_message_completion(conversation_id, message_id)
        
        # Process the response
        text_response, df_response, query_text = process_genie_response(client, conversation_id, message_id, complete_message)
        
        return text_response, df_response, query_text
        
    except Exception as e:
        # Handle specific errors
        if "429" in str(e) or "Too Many Requests" in str(e):
            return "Sorry, the system is currently experiencing high demand. Please try again in a few moments.", None
        elif "Conversation not found" in str(e):
            return "Sorry, the previous conversation has expired. Please try your query again to start a new conversation.", None
        else:
            logger.error(f"Error continuing conversation: {str(e)}")
            return f"Sorry, an error occurred: {str(e)}", None

def process_genie_response(client, conversation_id, message_id, complete_message) -> Tuple[str, Optional[pd.DataFrame], Optional[str]]:
    """
    Process the response from Genie
    
    Args:
        client: The GenieClient instance
        conversation_id: The conversation ID
        message_id: The message ID
        complete_message: The completed message response
        
    Returns:
        Tuple containing:
        - text_response: Either from a Genie text response or a query description
        - dataframe_response: DataFrame response if applicable, otherwise None
        - query_text: SQL query text if applicable, otherwise None
    """
    # Check attachments first
    attachments = complete_message.get("attachments", [])
    for attachment in attachments:
        attachment_id = attachment.get("attachment_id")
        
        # If there's text content in the attachment, return it
        if "text" in attachment and "content" in attachment["text"]:
            return attachment["text"]["content"], None, None
        
        # If there's a query, get the result
        elif "query" in attachment:
            query_text = attachment.get("query", {}).get("query", "")

            query_result = client.get_query_result(conversation_id, message_id, attachment_id)
            data_array = query_result.get('data_array', [])
            schema = query_result.get('schema', {})
            columns = [col.get('name') for col in schema.get('columns', [])]
            
            query_description = attachment.get("query", {}).get("description", "")
            logger.info(f"Query description: {query_description}")

            # If we have data, return as DataFrame
            if data_array:
                # If no columns from schema, create generic ones
                if not columns and data_array and len(data_array) > 0:
                    columns = [f"column_{i}" for i in range(len(data_array[0]))]
                
                df = pd.DataFrame(data_array, columns=columns)
                return query_description, df, query_text
    
    # If no attachments or no data in attachments, return text content
    if 'content' in complete_message:
        return "No response available for query: " + complete_message.get('content', ''), None, None
    
    return "No response available", None, None

def genie_query(question: str, conversation_id: str=None) -> Tuple[str, str, Optional[pd.DataFrame], Optional[str]]:
    """
    Main entry point for querying Genie.
    
    Args:
        question: The question to ask
        conversation_id: The conversation ID to continue, or None to start a new conversation
    Returns:
        Tuple containing:
        - conversation_id: The conversation ID
        - text_response: Either from a Genie text response or a query description
        - dataframe_response: DataFrame response if applicable, otherwise None
        - query_text: SQL query text if applicable, otherwise None
    """
    try:
        if conversation_id is None:
            conversation_id, text_response, df_response, query_text = start_new_conversation(question)
        else:
            text_response, df_response, query_text = continue_conversation(conversation_id, question)
        return conversation_id, text_response, df_response, query_text
            
    except Exception as e:
        logger.error(f"Error in conversation: {str(e)}. Please try again.")
        return f"Sorry, an error occurred: {str(e)}. Please try again.", None, None, None

def refresh_genie_token() -> None:
    """
    Explicitly refresh the Genie token.

    In theory not necesssary to call this because the main Genie functions all call GenieClient.update_headers(),
    but sometimes that doesn't work for some reason.
    """
    logger.info("Explicitly refreshing Genie token.")
    logger.info(f"Old token expiry time: {token_minter.expiry_time}")
    token_minter.get_token(force_refresh=True)
    logger.info(f"New token expiry time: {token_minter.expiry_time}")

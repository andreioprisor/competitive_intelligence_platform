import os
from dotenv import load_dotenv
import google.generativeai as genai
from google import genai as genai_client
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, ThinkingConfig, UserContent, ModelContent, Part, AutomaticFunctionCallingConfig
from google.genai import types
import requests
import json
import logging
import http
from urllib.parse import urlparse
load_dotenv()
logger = logging.getLogger(__name__)

class GeminiAPI:
    global_token_count_input = 0  # Track global token count across all instances
    global_token_count_output = 0  # Track global token count across all instances
    
    def __init__(self, model_id="gemini-2.5-flash"):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai_client.Client(api_key=self.gemini_api_key)
        self.model_id = model_id
        self.google_search_tool = Tool(google_search=GoogleSearch())
        self.chat_session = None # This will be used for conversations (where context retention is needed)
        
        # Configure genai for token counting
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        genai.configure(api_key=self.gemini_api_key)
        
        self.input_tokens = 0
        self.output_tokens = 0
        self.thinking_tokens = 0
    
    def count_tokens(self, text: str, model_name: str = "gemini-2.5-flash") -> int:
        """Count tokens in the given text using Gemini's token counter"""
        try:
            model = genai.GenerativeModel(model_name)
            token_count = model.count_tokens(text)
            return token_count.total_tokens
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            return 0
    
    def _extract_token_usage(self, response) -> dict:
        """
        Extract token usage from Gemini API response usage_metadata
        
        Args:
            response: GenerateContentResponse object
            
        Returns:
            dict: Token usage with keys: input_tokens, output_tokens, thinking_tokens, total_tokens
        """
        token_usage = {
            'input_tokens': 0,
            'output_tokens': 0, 
            'thinking_tokens': 0,
            'total_tokens': 0
        }
        
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = response.usage_metadata
                
                # Extract token counts
                if hasattr(usage_metadata, 'prompt_token_count') and usage_metadata.prompt_token_count:
                    token_usage['input_tokens'] = usage_metadata.prompt_token_count
                    
                if hasattr(usage_metadata, 'candidates_token_count') and usage_metadata.candidates_token_count:
                    token_usage['output_tokens'] = usage_metadata.candidates_token_count
                    
                if hasattr(usage_metadata, 'thoughts_token_count') and usage_metadata.thoughts_token_count:
                    token_usage['thinking_tokens'] = usage_metadata.thoughts_token_count
                    
                if hasattr(usage_metadata, 'total_token_count') and usage_metadata.total_token_count:
                    token_usage['total_tokens'] = usage_metadata.total_token_count
                else:
                    # Calculate total if not provided
                    token_usage['total_tokens'] = (token_usage['input_tokens'] + 
                                                 token_usage['output_tokens'] + 
                                                 token_usage['thinking_tokens'])
                    
                logger.debug(f"Extracted token usage from API response: {token_usage}")
                return token_usage
                
        except Exception as e:
            logger.warning(f"Failed to extract token usage from response: {e}")
        
        # Return empty counts if extraction failed
        logger.debug("Could not extract token usage from response, returning zeros")
        return token_usage
    
    def get_completion(self, prompt: str, model_name="gemini-2.5-flash", thinking_budget=512, response_schema=None, temperature=0.8) -> str:
        """Get completion from Gemini with token usage logging"""
        try:
            # Build config
            if thinking_budget is None:
                thinking_budget = 0
                
            config = GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget),
                temperature=temperature,
                automatic_function_calling=AutomaticFunctionCallingConfig(
                    disable=True,  # Enable automatic function calling
                ),
            )
            
            # Add response schema if provided
            if response_schema is not None:
                config.response_mime_type = "application/json"
                config.response_schema = response_schema
            
            # Generate content using the Gemini client
            response = self.client.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=config,
            )
            
            # Safely extract text content from response
            full_text = response.text if hasattr(response, 'text') else ""
            
            # Only clean markdown if no schema is provided (backward compatibility)
            if response_schema is None:
                full_text = full_text.strip().replace("```json", "").replace("```", "")
            
            # Extract token usage from API response
            token_usage = self._extract_token_usage(response)
            input_tokens = token_usage['input_tokens']
            output_tokens = token_usage['output_tokens'] + token_usage['thinking_tokens']
            thinking_tokens = token_usage['thinking_tokens']
            total_tokens = token_usage['total_tokens']
            
            # Fallback to manual counting if API didn't provide usage metadata
            if total_tokens == 0:
                logger.warning("No token usage metadata in response, falling back to manual counting")
                input_tokens = self.count_tokens(prompt, model_name)
                output_tokens = self.count_tokens(full_text, model_name)
                thinking_tokens = 0
                total_tokens = input_tokens + output_tokens
            
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.thinking_tokens += thinking_tokens
            
            # Update global token counters
            GeminiAPI.global_token_count_input += input_tokens
            GeminiAPI.global_token_count_output += output_tokens
            
            # Enhanced logging with thinking tokens
            if thinking_tokens > 0:
                logger.info(f"Completion Token usage - Input: {input_tokens}, Output: {output_tokens}, Thinking: {thinking_tokens}, Total: {total_tokens}")
            else:
                logger.info(f"Completion Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            logger.info(f"Global token usage - Input: {GeminiAPI.global_token_count_input}, Output: {GeminiAPI.global_token_count_output}, Total: {GeminiAPI.global_token_count_input + GeminiAPI.global_token_count_output}")
            # logger.debug("Full response: %s", response)
            return full_text
            
        except Exception as e:
            logger.error(f"Error getting completion from Gemini: {e}")
            # Log the response object for debugging if it exists
            if 'response' in locals():
                logger.error(f"Response object: {response}")
            raise

    def get_google_search_response(self, prompt: str, model_name="gemini-2.5-pro", thinking_budget=1024, temperature=0.8) -> dict:
        """Get completion with Google Search access and token logging"""
        try:
            # Build config
            config = GenerateContentConfig(
                tools=[self.google_search_tool],
                response_modalities=["TEXT"],
                temperature=temperature,
                thinking_config=ThinkingConfig(
                    thinking_budget=thinking_budget,
                ),
            )
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config
            )
            
            # Extract text content using the simple approach from documentation
            full_text = ""
            if hasattr(response, 'text') and response.text:
                full_text = response.text
            else:
                # Fallback to the complex extraction method
                text_content = []
                if (hasattr(response, 'candidates') and 
                    response.candidates and 
                    len(response.candidates) > 0 and
                    hasattr(response.candidates[0], 'content') and
                    response.candidates[0].content and
                    hasattr(response.candidates[0].content, 'parts') and
                    response.candidates[0].content.parts):
                    
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'text') and part.text:
                            text_content.append(part.text)
                            
                    full_text = "\n".join(text_content)
                else:
                    logger.warning(f"Unexpected response structure: {response}")
                    full_text = "No text content found in response"
            
            # Extract token usage from API response
            token_usage = self._extract_token_usage(response)
            input_tokens = token_usage['input_tokens']
            output_tokens = token_usage['output_tokens'] 
            thinking_tokens = token_usage['thinking_tokens']
            total_tokens = token_usage['total_tokens']
            
            # Fallback to manual counting if API didn't provide usage metadata
            if total_tokens == 0:
                logger.warning("No token usage metadata in response, falling back to manual counting")
                input_tokens = self.count_tokens(prompt, model_name)
                output_tokens = self.count_tokens(full_text, model_name)
                thinking_tokens = 0
                total_tokens = input_tokens + output_tokens
            
            # Update global counters
            GeminiAPI.global_token_count_input += input_tokens
            GeminiAPI.global_token_count_output += output_tokens
            
            # Get grounding metadata if available
            grounding_metadata = None
            if (hasattr(response, 'candidates') and 
                response.candidates and 
                len(response.candidates) > 0 and
                hasattr(response.candidates[0], 'grounding_metadata') and 
                response.candidates[0].grounding_metadata and
                hasattr(response.candidates[0].grounding_metadata, 'search_entry_point') and
                response.candidates[0].grounding_metadata.search_entry_point is not None):
                grounding_metadata = response.candidates[0].grounding_metadata.search_entry_point.rendered_content
            
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
            self.thinking_tokens += thinking_tokens

            # Enhanced logging with thinking tokens
            if thinking_tokens > 0:
                logger.info(f"Google Search Token usage - Input: {input_tokens}, Output: {output_tokens}, Thinking: {thinking_tokens}, Total: {total_tokens}")
            else:
                logger.info(f"Google Search Token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            logger.info(f"Global token usage - Input: {GeminiAPI.global_token_count_input}, Output: {GeminiAPI.global_token_count_output}, Total: {GeminiAPI.global_token_count_input + GeminiAPI.global_token_count_output}")
            
            logger.info("Full response: %s", response)

            return full_text
            
        except Exception as e:
            logger.error(f"Error getting Google Search response: {e}")
            # Log the full response for debugging
            if 'response' in locals():
                logger.error(f"Response object: {response}")
            raise
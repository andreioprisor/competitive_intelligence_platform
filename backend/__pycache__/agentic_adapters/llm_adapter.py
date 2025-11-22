import os
import json
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

import google.generativeai as genai
from google import genai as genai_client
from google.genai.types import AutomaticFunctionCallingConfig, GenerateContentConfig, ThinkingConfig
from google.genai import types
from leadora.adapters.api_clients import GeminiAPI

load_dotenv()
logger = logging.getLogger(__name__)

class LLMAdapter:
    """Simplified Gemini adapter for QIA agent"""
    
    def __init__(self, model_id: str = "gemini-flash-latest"):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        # Configure both genai clients (same as api_clients.py)
        self.client = genai_client.Client(api_key=self.api_key)
        self.model_id = model_id
        genai.configure(api_key=self.api_key)  # For token counting
        
        # Track token usage
        self.total_input_tokens = 0
        self.total_output_tokens = 0
    
    def count_tokens(self, text: str, model_name: str = "gemini-flash-latest") -> int:
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
    
    def get_completion(
        self,
        prompt: str,
        temperature: float = 0.7,
        response_schema = None,  # Pydantic model class or None
        max_tokens: int = 20000,
        thinking_budget: int = 0,
        model: str = None
    ):
        """
        Get completion from Gemini with optional Pydantic structured output

        Args:
            prompt: The prompt text
            temperature: Temperature for generation (0.0-1.0)
            response_schema: Optional Pydantic model class for structured output
            max_tokens: Maximum tokens to generate
            thinking_budget: Tokens allocated for thinking (extended thinking)
            model: Optional model override

        Returns:
            - If response_schema is provided: Pydantic model instance
            - Otherwise: Generated text string
        """
        try:
            # Build config
            config = GenerateContentConfig(
                temperature=temperature,
                automatic_function_calling=AutomaticFunctionCallingConfig(
                    disable=True,
                ),
                thinking_config=ThinkingConfig(
                    thinking_budget=thinking_budget,
                    include_thoughts=True,
                )
            )

            # Add Pydantic schema if provided
            if response_schema is not None:
                config.response_mime_type = "application/json"
                config.response_schema = response_schema

            # Use current model or provided model
            current_model = model if model else self.model_id

            # Generate content using the Gemini client
            response = self.client.models.generate_content(
                model=current_model,
                contents=[prompt],
                config=config,
            )

            # If schema provided, return parsed Pydantic object
            if response_schema is not None and hasattr(response, "parsed") and response.parsed is not None:
                result = response.parsed
            else:
                # Otherwise extract text and clean markdown
                result_text = response.text if hasattr(response, 'text') else ""
                result = result_text.strip().replace("```json", "").replace("```", "")
                result_text = result  # For token counting below
            
            # Extract token usage from API response (same as api_clients.py)
            token_usage = self._extract_token_usage(response)
            input_tokens = token_usage['input_tokens']
            output_tokens = token_usage['output_tokens'] + token_usage['thinking_tokens']
            thinking_tokens = token_usage['thinking_tokens']
            total_tokens = token_usage['total_tokens']
            
            # Fallback to manual counting if API didn't provide usage metadata
            if total_tokens == 0:
                logger.warning("No token usage metadata in response, falling back to manual counting")
                input_tokens = self.count_tokens(prompt, current_model)
                # For Pydantic results, count tokens from the JSON representation
                if response_schema is not None:
                    result_str = str(result)
                else:
                    result_str = result_text
                output_tokens = self.count_tokens(result_str, current_model)
                thinking_tokens = 0
                total_tokens = input_tokens + output_tokens
            
            # Update totals
            self.total_input_tokens += input_tokens
            self.total_output_tokens += output_tokens
            
            # Enhanced logging with thinking tokens
            logger.info(f"Generating completion for prompt: {prompt[:50]}... (max {max_tokens} tokens). Prompt tokens: {input_tokens}")
            if thinking_tokens > 0:
                logger.info(f"LLM tokens - Input: {input_tokens}, Output: {output_tokens}, Thinking: {thinking_tokens}, Total: {total_tokens}")
            else:
                logger.info(f"LLM tokens - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")

            return result
            
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise
    
    def get_structured_output(
        self,
        prompt: str,
        output_schema = None,
        response_format = None,
        thinking_budget: int = 0,
        temperature: float = 0.3
    ):
        """
        Get structured output from Gemini

        TWO MODES:
        1. With schema (Pydantic model): Uses native Gemini validation, returns Pydantic instance
        2. Without schema: Uses prompt-based JSON, parses string response to dict

        Args:
            prompt: The prompt text
            output_schema: (Optional) Pydantic model class - deprecated, use response_format
            response_format: (Optional) Pydantic model class for structured output
            thinking_budget: Tokens allocated for thinking
            temperature: Lower temperature for more consistent structure

        Returns:
            - If schema provided: Pydantic model instance
            - If no schema: Parsed JSON dict from string response
        """
        # Handle both parameter names
        schema = response_format if response_format is not None else output_schema

        # CASE 1: Schema provided - use Pydantic validation
        if schema is not None:
            return self.get_completion(
                prompt=prompt,
                temperature=temperature,
                response_schema=schema,
                thinking_budget=thinking_budget
            )

        # CASE 2: No schema - use prompt-based JSON parsing (existing behavior)
        try:
            # Add JSON instruction to prompt
            json_prompt = f"{prompt}\n\nPlease respond with valid JSON only. Format your response as a JSON object."

            # Get completion as text
            json_str = self.get_completion(
                prompt=json_prompt,
                temperature=temperature,
                response_schema=None,  # No schema
                thinking_budget=thinking_budget,
            )

            # Parse JSON from string
            if isinstance(json_str, str):
                # Clean up markdown if present
                json_str = json_str.strip()
                if json_str.startswith("```"):
                    lines = json_str.split("\n")
                    # Find the start and end of JSON block
                    start_idx = 0
                    end_idx = len(lines)

                    for i, line in enumerate(lines):
                        if line.strip().startswith("```"):
                            if start_idx == 0:
                                start_idx = i + 1
                            else:
                                end_idx = i
                                break

                    json_str = "\n".join(lines[start_idx:end_idx])

                return json.loads(json_str)
            else:
                return json_str

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {json_str}")
            # Return a minimal valid response
            return {"error": "Failed to parse LLM response", "raw": str(json_str)}
        except Exception as e:
            logger.error(f"Structured output generation failed: {e}")
            raise
    
    
    def format_prompt_with_template(
        self,
        template_path: str,
        **kwargs
    ) -> str:
        """
        Load and format a prompt template
        
        Args:
            template_path: Path to markdown template
            **kwargs: Variables to substitute in template
            
        Returns:
            Formatted prompt string
        """
        try:
            with open(template_path, 'r') as f:
                template = f.read()
            
            # Simple string formatting
            for key, value in kwargs.items():
                # Convert complex objects to JSON for insertion
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, indent=2)
                elif value is None:
                    value = "Not provided"
                else:
                    value = str(value)
                
                template = template.replace(f"{{{key}}}", value)
            
            return template
            
        except Exception as e:
            logger.error(f"Failed to format prompt template: {e}")
            raise
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get current token usage statistics"""
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens
        }
    
    def reset_token_usage(self):
        """Reset token counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
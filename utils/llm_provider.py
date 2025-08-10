"""
LLM Provider Utility

Handles communication with OpenAI-compatible LLM endpoints
Configured via .secrets.toml file in the root directory
"""

import sys
import toml
from openai import OpenAI
from typing import List, Dict, Any


class LLMProvider:
    def __init__(self, secrets_path: str = '.secrets.toml'):
        """Initialize LLM provider with configuration from secrets file."""
        self.config = self._load_config(secrets_path)
        self.client = OpenAI(
            base_url=self.config['API_URL'],
            api_key=self.config['API_KEY']
        )
    
    def _load_config(self, secrets_path: str) -> Dict[str, str]:
        """Load API configuration from secrets file."""
        try:
            with open(secrets_path, 'r') as f:
                secrets = toml.load(f)
            
            required_keys = ['API_KEY', 'API_URL']
            for key in required_keys:
                if key not in secrets:
                    raise KeyError(f"Missing required key '{key}' in secrets file")
            
            return secrets
            
        except FileNotFoundError:
            print(f"Error: Secrets file '{secrets_path}' not found.", file=sys.stderr)
            print("Please create .secrets.toml based on .secrets.example.toml", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error loading secrets file: {e}", file=sys.stderr)
            sys.exit(1)
    
    def generate_completion(
        self, 
        messages: List[Dict[str, str]], 
        model_config: Dict[str, Any]
    ) -> str:
        """Generate a completion using the configured LLM provider."""
        
        model_name = model_config.get('model_name', 'llama3.1:8b')
        
        # Extract generation parameters (using Ollama-compatible defaults)
        temperature = model_config.get('temperature', 0.8)  # Ollama default
        max_tokens = model_config.get('max_tokens', 300)    # Reasonable for conversations
        top_p = model_config.get('top_p', 0.9)              # Ollama default
        frequency_penalty = model_config.get('frequency_penalty', 0.0)  # Ollama default
        presence_penalty = model_config.get('presence_penalty', 0.0)    # Ollama default
        
        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error generating completion: {e}", file=sys.stderr)
            raise
    
 
"""
LLM Provider Utility
Handles communication with OpenAI-compatible LLM endpoints
Configured via .secrets.toml file in the root directory
"""
import sys
import tomllib
from openai import OpenAI
from typing import List, Dict, Any, Optional

class LLMProvider:
    def __init__(self, provider_name: str = 'OLLAMA', secrets_path: str = '.secrets.toml'):
        """Initialize LLM provider with configuration from secrets file.
        
        Args:
            provider_name: Name of the provider to use from the secrets file
            secrets_path: Path to the TOML secrets file
        """
        self.providers_config = self._load_config(secrets_path)
        self.current_provider = None
        self.set_provider(provider_name)
    
    def _load_config(self, secrets_path: str) -> Dict[str, Dict[str, str]]:
        """Load API configuration from secrets file with multiple providers."""
        try:
            with open(secrets_path, 'rb') as f:
                secrets = tomllib.load(f)
            
            # Validate each provider has required keys
            for provider, config in secrets.items():
                if provider.startswith('_'):  # Skip comment sections
                    continue
                    
                required_keys = ['API_KEY', 'API_URL']
                for key in required_keys:
                    if key not in config:
                        raise KeyError(f"Missing required key '{key}' for provider '{provider}'")
            
            return secrets
            
        except FileNotFoundError:
            print(f"Error: Secrets file '{secrets_path}' not found.", file=sys.stderr)
            print("Please create .secrets.toml based on .secrets.example.toml", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error loading secrets file: {e}", file=sys.stderr)
            sys.exit(1)
    
    def set_provider(self, provider_name: str) -> None:
        """Set the active LLM provider.
        
        Args:
            provider_name: Name of the provider to use
        """
        if provider_name not in self.providers_config:
            available = list(self.providers_config.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available providers: {available}")
        
        self.current_provider = provider_name
        provider_config = self.providers_config[provider_name]
        
        # Initialize the OpenAI client for the selected provider
        self.client = OpenAI(
            base_url=provider_config['API_URL'],
            api_key=provider_config['API_KEY']
        )
        print(f"Active provider set to: {provider_name}")
    
    def get_available_providers(self) -> List[str]:
        """Return a list of available provider names."""
        # Filter out any sections that might be comments or metadata
        return [p for p in self.providers_config.keys() if not p.startswith('_')]
    
    def generate_completion(
        self, 
        messages: List[Dict[str, str]], 
        model_config: Dict[str, Any],
        provider_name: Optional[str] = None
    ) -> str:
        """Generate a completion using the configured LLM provider.
        
        Args:
            messages: The messages to send to the LLM
            model_config: Configuration parameters for the model
            provider_name: Optional provider name to use for this request only
        
        Returns:
            The generated text from the LLM
        """
        # Temporarily switch provider if specified
        original_provider = self.current_provider
        if provider_name and provider_name != self.current_provider:
            self.set_provider(provider_name)
        
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
            
            result = response.choices[0].message.content
            
            # Restore original provider if we temporarily switched
            if provider_name and provider_name != original_provider:
                self.set_provider(original_provider)
                
            return result
            
        except Exception as e:
            # Restore original provider even if there was an error
            if provider_name and provider_name != original_provider:
                self.set_provider(original_provider)
                
            print(f"Error generating completion with provider {self.current_provider}: {e}", file=sys.stderr)
            raise
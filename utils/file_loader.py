"""
File loading utilities for conversation generation.

Handles loading and resolving of:
- Conversation configuration files
- Persona files and their associated prompts
- Vignette files (both JSON cards and direct text)
"""

import json
from pathlib import Path
from typing import Dict, Any


class FileLoader:
    """Handles loading and resolving all configuration and content files."""
    
    def __init__(self, config_path: str):
        """Initialize with the main conversation config file path."""
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    def load_conversation_config(self) -> Dict[str, Any]:
        """Load the main conversation configuration file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if 'conversation_card' not in config:
                raise ValueError("Configuration file missing 'conversation_card' structure")
            
            return config['conversation_card']
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Error loading conversation config from {self.config_path}: {e}")
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to config directory."""
        if file_path.startswith('./') or file_path.startswith('../'):
            resolved_path = self.config_path.parent / file_path
        else:
            resolved_path = Path(file_path)
        
        return resolved_path.resolve()
    
    def load_participants(self, config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Load persona configurations for all participants."""
        participants = {}
        
        for participant_id, participant_config in config['participants'].items():
            try:
                persona_data = self._load_single_persona(participant_config['persona_file'])
                
                participants[participant_id] = {
                    'config': participant_config,
                    'persona': persona_data
                }
                
            except Exception as e:
                raise ValueError(f"Error loading persona for {participant_id}: {e}")
        
        return participants
    
    def _load_single_persona(self, persona_file: str) -> Dict[str, Any]:
        """Load a single persona file and resolve its prompt content."""
        persona_path = self._resolve_path(persona_file)
        
        if not persona_path.exists():
            raise FileNotFoundError(f"Persona file not found: {persona_path}")
        
        try:
            with open(persona_path, 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
            
            if 'persona_card' not in persona_data:
                raise ValueError("Persona file missing 'persona_card' structure")
            
            persona_card = persona_data['persona_card']
            
            # Load prompt content if specified as external file
            if 'prompt_file' in persona_card['persona_prompt']:
                prompt_content = self._load_prompt_file(
                    persona_card['persona_prompt']['prompt_file'], 
                    persona_path.parent
                )
                persona_card['persona_prompt']['content'] = prompt_content
            
            return persona_card
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Error parsing persona file {persona_path}: {e}")
    
    def _load_prompt_file(self, prompt_file: str, base_dir: Path) -> str:
        """Load prompt content from an external file."""
        # Resolve prompt file path relative to persona file directory
        if prompt_file.startswith('./') or prompt_file.startswith('../'):
            prompt_path = base_dir / prompt_file
        else:
            prompt_path = Path(prompt_file)
        
        prompt_path = prompt_path.resolve()
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error reading prompt file {prompt_path}: {e}")
    
    def load_vignette(self, config: Dict[str, Any]) -> str:
        """Load vignette content - handles both JSON vignette cards and direct text files."""
        vignette_file = config['scenario']['vignette_file']
        vignette_path = self._resolve_path(vignette_file)
        
        if not vignette_path.exists():
            raise FileNotFoundError(f"Vignette file not found: {vignette_path}")
        
        try:
            if vignette_path.suffix.lower() == '.json':
                return self._load_json_vignette(vignette_path)
            else:
                return self._load_text_vignette(vignette_path)
                
        except Exception as e:
            raise ValueError(f"Error loading vignette from {vignette_path}: {e}")
    
    def _load_json_vignette(self, vignette_path: Path) -> str:
        """Load vignette from JSON vignette card format."""
        with open(vignette_path, 'r', encoding='utf-8') as f:
            vignette_data = json.load(f)
        
        if 'vignette_card' in vignette_data:
            vignette_card = vignette_data['vignette_card']
            
            if 'content' in vignette_card and 'vignette_file' in vignette_card['content']:
                # Load content from external file
                content_file = vignette_card['content']['vignette_file']
                content_path = self._resolve_content_file_path(content_file, vignette_path.parent)
                
                with open(content_path, 'r', encoding='utf-8') as cf:
                    return cf.read()
            else:
                raise ValueError("Vignette JSON missing content structure")
        else:
            # If no vignette_card structure, treat as direct JSON content
            return json.dumps(vignette_data, indent=2)
    
    def _load_text_vignette(self, vignette_path: Path) -> str:
        """Load vignette from direct text file."""
        with open(vignette_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _resolve_content_file_path(self, content_file: str, base_dir: Path) -> Path:
        """Resolve content file path relative to vignette file directory."""
        if content_file.startswith('./') or content_file.startswith('../'):
            content_path = base_dir / content_file
        else:
            content_path = Path(content_file)
        
        content_path = content_path.resolve()
        
        if not content_path.exists():
            raise FileNotFoundError(f"Vignette content file not found: {content_path}")
        
        return content_path
    
    def get_config_path(self) -> str:
        """Get the original config file path as string."""
        return str(self.config_path)
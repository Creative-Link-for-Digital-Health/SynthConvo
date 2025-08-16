#!/usr/bin/env python3
"""
Interface Validator Library

Validates conversation interface files and their dependencies.
Provides comprehensive validation for personas, vignettes, modifiers, and conversation configs.
"""

import json
import os
from typing import Dict, List, Any, Tuple
from pathlib import Path


class InterfaceValidator:
    """Validates conversation interface files and their dependencies."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
        self.validation_results = []
    
    def validate_all(self) -> Tuple[bool, List[str]]:
        """Run all validations and return success status and messages."""
        self.validation_results = []
        
        try:
            # Load main config
            if not self._validate_conversation_config():
                return False, self.validation_results
            
            # Validate all referenced files
            self._validate_participants()
            self._validate_vignette()
            self._validate_modifiers()
            
            # Summary
            errors = [msg for msg in self.validation_results if msg.startswith("❌")]
            warnings = [msg for msg in self.validation_results if msg.startswith("⚠️")]
            success = len(errors) == 0
            
            if success:
                self.validation_results.append("✅ All interfaces validated successfully!")
            else:
                self.validation_results.append(f"❌ Validation failed with {len(errors)} errors and {len(warnings)} warnings")
            
            return success, self.validation_results
            
        except Exception as e:
            self.validation_results.append(f"❌ Validation failed with exception: {e}")
            return False, self.validation_results
    
    def _validate_conversation_config(self) -> bool:
        """Validate the main conversation configuration file."""
        try:
            if not os.path.exists(self.config_path):
                self.validation_results.append(f"❌ Conversation config file not found: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if 'conversation_card' not in config_data:
                self.validation_results.append("❌ Missing 'conversation_card' key in config")
                return False
            
            self.config = config_data['conversation_card']
            self.validation_results.append("✅ Conversation config loaded successfully")
            
            # Validate required sections
            required_sections = ['participants', 'scenario', 'conversation_parameters']
            for section in required_sections:
                if section not in self.config:
                    self.validation_results.append(f"❌ Missing required section: {section}")
                    return False
                else:
                    self.validation_results.append(f"✅ Found required section: {section}")
            
            return True
            
        except json.JSONDecodeError as e:
            self.validation_results.append(f"❌ Invalid JSON in conversation config: {e}")
            return False
        except Exception as e:
            self.validation_results.append(f"❌ Error reading conversation config: {e}")
            return False
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to config directory."""
        if file_path.startswith('./') or file_path.startswith('../'):
            config_dir = Path(self.config_path).parent
            resolved_path = config_dir / file_path
        else:
            resolved_path = Path(file_path)
        
        return resolved_path.resolve()
    
    def _validate_participants(self):
        """Validate all participant personas and their dependencies."""
        participants = self.config.get('participants', {})
        
        if not participants:
            self.validation_results.append("❌ No participants defined")
            return
        
        self.validation_results.append(f"✅ Found {len(participants)} participants")
        
        for participant_id, participant_config in participants.items():
            self.validation_results.append(f"\n--- Validating {participant_id} ---")
            
            # Check persona file reference
            if 'persona_file' not in participant_config:
                self.validation_results.append(f"❌ {participant_id}: Missing persona_file")
                continue
            
            persona_file = participant_config['persona_file']
            persona_path = self._resolve_path(persona_file)
            
            # Check if persona file exists
            if not persona_path.exists():
                self.validation_results.append(f"❌ {participant_id}: Persona file not found: {persona_path}")
                continue
            
            self.validation_results.append(f"✅ {participant_id}: Persona file found: {persona_path}")
            
            # Validate persona file content
            try:
                with open(persona_path, 'r', encoding='utf-8') as f:
                    persona_data = json.load(f)
                
                if 'persona_card' not in persona_data:
                    self.validation_results.append(f"❌ {participant_id}: Missing 'persona_card' in persona file")
                    continue
                
                persona_card = persona_data['persona_card']
                
                # Check required sections in persona
                required_persona_sections = ['model_config', 'persona_prompt', 'metadata']
                for section in required_persona_sections:
                    if section in persona_card:
                        self.validation_results.append(f"✅ {participant_id}: Found {section}")
                    else:
                        self.validation_results.append(f"⚠️ {participant_id}: Missing optional section: {section}")
                
                # Validate prompt file if referenced
                if 'persona_prompt' in persona_card and 'prompt_file' in persona_card['persona_prompt']:
                    prompt_file = persona_card['persona_prompt']['prompt_file']
                    
                    if prompt_file.startswith('./') or prompt_file.startswith('../'):
                        prompt_path = persona_path.parent / prompt_file
                    else:
                        prompt_path = Path(prompt_file)
                    
                    prompt_path = prompt_path.resolve()
                    
                    if prompt_path.exists():
                        self.validation_results.append(f"✅ {participant_id}: Prompt file found: {prompt_path}")
                        
                        # Check if prompt file has content
                        try:
                            with open(prompt_path, 'r', encoding='utf-8') as pf:
                                prompt_content = pf.read().strip()
                                if prompt_content:
                                    self.validation_results.append(f"✅ {participant_id}: Prompt file has content ({len(prompt_content)} chars)")
                                else:
                                    self.validation_results.append(f"⚠️ {participant_id}: Prompt file is empty")
                        except Exception as e:
                            self.validation_results.append(f"❌ {participant_id}: Error reading prompt file: {e}")
                    else:
                        self.validation_results.append(f"❌ {participant_id}: Prompt file not found: {prompt_path}")
                
                # Validate model config
                if 'model_config' in persona_card:
                    model_config = persona_card['model_config']
                    if 'model_name' in model_config:
                        self.validation_results.append(f"✅ {participant_id}: Model configured: {model_config['model_name']}")
                    else:
                        self.validation_results.append(f"⚠️ {participant_id}: No model_name specified")
                
                # Check modifier settings
                apply_modifiers = participant_config.get('apply_modifiers', False)
                if apply_modifiers:
                    applied_modifiers = participant_config.get('applied_modifiers', [])
                    if applied_modifiers:
                        self.validation_results.append(f"✅ {participant_id}: Modifiers configured: {applied_modifiers}")
                    else:
                        self.validation_results.append(f"⚠️ {participant_id}: apply_modifiers=true but no applied_modifiers specified")
                else:
                    self.validation_results.append(f"✅ {participant_id}: No modifiers (as configured)")
                
                # Check description and llm_role
                if 'description' in participant_config:
                    self.validation_results.append(f"✅ {participant_id}: Description: {participant_config['description']}")
                else:
                    self.validation_results.append(f"⚠️ {participant_id}: No description provided")
                
                if 'llm_role' in participant_config:
                    llm_role = participant_config['llm_role']
                    if llm_role in ['user', 'assistant']:
                        self.validation_results.append(f"✅ {participant_id}: LLM role: {llm_role}")
                    else:
                        self.validation_results.append(f"❌ {participant_id}: Invalid llm_role '{llm_role}' (must be 'user' or 'assistant')")
                else:
                    self.validation_results.append(f"⚠️ {participant_id}: No llm_role specified")
                
            except json.JSONDecodeError as e:
                self.validation_results.append(f"❌ {participant_id}: Invalid JSON in persona file: {e}")
            except Exception as e:
                self.validation_results.append(f"❌ {participant_id}: Error reading persona file: {e}")
    
    def _validate_vignette(self):
        """Validate vignette file and content."""
        self.validation_results.append("\n--- Validating Vignette ---")
        
        scenario = self.config.get('scenario', {})
        if 'vignette_file' not in scenario:
            self.validation_results.append("❌ Missing vignette_file in scenario")
            return
        
        vignette_file = scenario['vignette_file']
        vignette_path = self._resolve_path(vignette_file)
        
        if not vignette_path.exists():
            self.validation_results.append(f"❌ Vignette file not found: {vignette_path}")
            return
        
        self.validation_results.append(f"✅ Vignette file found: {vignette_path}")
        
        # Check vignette content - handle both JSON and text files
        try:
            if vignette_path.suffix.lower() == '.json':
                with open(vignette_path, 'r', encoding='utf-8') as f:
                    vignette_data = json.load(f)
                
                if 'vignette_card' in vignette_data:
                    self.validation_results.append("✅ Vignette JSON structure is valid")
                    vignette_card = vignette_data['vignette_card']
                    
                    if 'content' in vignette_card and 'vignette_file' in vignette_card['content']:
                        content_file = vignette_card['content']['vignette_file']
                        content_path = vignette_path.parent / content_file
                        
                        if content_path.exists():
                            with open(content_path, 'r', encoding='utf-8') as cf:
                                content_text = cf.read().strip()
                                if content_text:
                                    self.validation_results.append(f"✅ Vignette content file has text ({len(content_text)} chars)")
                                else:
                                    self.validation_results.append("❌ Vignette content file is empty")
                        else:
                            self.validation_results.append(f"❌ Vignette content file not found: {content_path}")
                else:
                    self.validation_results.append("⚠️ Vignette JSON doesn't have expected structure")
            else:
                # Direct text file
                with open(vignette_path, 'r', encoding='utf-8') as f:
                    vignette_content = f.read().strip()
                    if vignette_content:
                        self.validation_results.append(f"✅ Vignette has content ({len(vignette_content)} chars)")
                        if len(vignette_content) < 100:
                            self.validation_results.append("⚠️ Vignette content seems quite short")
                    else:
                        self.validation_results.append("❌ Vignette file is empty")
        except Exception as e:
            self.validation_results.append(f"❌ Error reading vignette file: {e}")
    
    def _validate_modifiers(self):
        """Validate modifier configuration and file."""
        self.validation_results.append("\n--- Validating Modifiers ---")
        
        if 'modifier_config' not in self.config:
            self.validation_results.append("⚠️ No modifier_config section (modifiers disabled)")
            return
        
        modifier_config = self.config['modifier_config']
        if 'modifiers_file' not in modifier_config:
            self.validation_results.append("❌ Missing modifiers_file in modifier_config")
            return
        
        modifier_file = modifier_config['modifiers_file']
        modifier_path = self._resolve_path(modifier_file)
        
        if not modifier_path.exists():
            self.validation_results.append(f"❌ Modifier file not found: {modifier_path}")
            return
        
        self.validation_results.append(f"✅ Modifier file found: {modifier_path}")
        
        # Validate modifier file content
        try:
            with open(modifier_path, 'r', encoding='utf-8') as f:
                modifier_data = json.load(f)
            
            if 'modifying_adjectives' not in modifier_data:
                self.validation_results.append("❌ Missing 'modifying_adjectives' in modifier file")
                return
            
            modifying_adjectives = modifier_data['modifying_adjectives']
            category_count = len(modifying_adjectives)
            self.validation_results.append(f"✅ Found {category_count} modifier categories")
            
            # Check if requested modifier categories exist
            participants = self.config.get('participants', {})
            for participant_id, participant_config in participants.items():
                if participant_config.get('apply_modifiers', False):
                    applied_modifiers = participant_config.get('applied_modifiers', [])
                    for category in applied_modifiers:
                        if category in modifying_adjectives:
                            self.validation_results.append(f"✅ {participant_id}: Modifier category '{category}' exists")
                        else:
                            self.validation_results.append(f"❌ {participant_id}: Modifier category '{category}' not found in modifier file")
            
        except json.JSONDecodeError as e:
            self.validation_results.append(f"❌ Invalid JSON in modifier file: {e}")
        except Exception as e:
            self.validation_results.append(f"❌ Error reading modifier file: {e}")


def validate_conversation_interface(config_path: str) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a conversation interface.
    
    Args:
        config_path: Path to the conversation configuration file
        
    Returns:
        Tuple of (is_valid, validation_messages)
    """
    validator = InterfaceValidator(config_path)
    return validator.validate_all()


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python interface_validator.py <conversation_config_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    is_valid, messages = validate_conversation_interface(config_path)
    
    print("🔍 Interface Validation Results:")
    print("=" * 60)
    for message in messages:
        print(message)
    print("=" * 60)
    
    if is_valid:
        print("🎉 Validation passed!")
        sys.exit(0)
    else:
        print("💥 Validation failed!")
        sys.exit(1)
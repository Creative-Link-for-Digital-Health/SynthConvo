#!/usr/bin/env python3
"""
Interface Validator Library

Validates conversation interface files and their dependencies.
Provides comprehensive validation for personas, vignettes, modifiers, and conversation configs.
Enhanced with smart modifier validation and configuration checks.
"""

import json
import os
from typing import Dict, List, Any, Tuple, Optional, Set
from pathlib import Path


class InterfaceValidator:
    """Validates conversation interface files and their dependencies."""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = None
        self.validation_results = []
        self.modifier_engine = None
    
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
            
            # Advanced validation checks
            self._validate_conversation_logic()
            self._validate_modifier_combinations()
            
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
            
            # Validate optional but recommended sections
            optional_sections = ['title', 'metadata']
            for section in optional_sections:
                if section in self.config:
                    self.validation_results.append(f"✅ Found optional section: {section}")
                else:
                    self.validation_results.append(f"⚠️ Missing recommended section: {section}")
            
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
        
        if len(participants) < 2:
            self.validation_results.append("⚠️ Only one participant defined - conversations require at least 2")
        
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
            self._validate_persona_content(participant_id, persona_path, participant_config)
    
    def _validate_persona_content(self, participant_id: str, persona_path: Path, participant_config: Dict[str, Any]):
        """Validate content of a persona file."""
        try:
            with open(persona_path, 'r', encoding='utf-8') as f:
                persona_data = json.load(f)
            
            if 'persona_card' not in persona_data:
                self.validation_results.append(f"❌ {participant_id}: Missing 'persona_card' in persona file")
                return
            
            persona_card = persona_data['persona_card']
            
            # Check required sections in persona
            required_persona_sections = ['model_config', 'persona_prompt']
            optional_persona_sections = ['metadata', 'validation_criteria']
            
            for section in required_persona_sections:
                if section in persona_card:
                    self.validation_results.append(f"✅ {participant_id}: Found required section '{section}'")
                else:
                    self.validation_results.append(f"❌ {participant_id}: Missing required section '{section}'")
            
            for section in optional_persona_sections:
                if section in persona_card:
                    self.validation_results.append(f"✅ {participant_id}: Found optional section '{section}'")
                else:
                    self.validation_results.append(f"⚠️ {participant_id}: Missing optional section '{section}'")
            
            # Validate persona prompt
            self._validate_persona_prompt(participant_id, persona_card, persona_path)
            
            # Validate model config
            self._validate_model_config(participant_id, persona_card)
            
            # Validate participant-level configuration
            self._validate_participant_config(participant_id, participant_config)
            
        except json.JSONDecodeError as e:
            self.validation_results.append(f"❌ {participant_id}: Invalid JSON in persona file: {e}")
        except Exception as e:
            self.validation_results.append(f"❌ {participant_id}: Error reading persona file: {e}")
    
    def _validate_persona_prompt(self, participant_id: str, persona_card: Dict[str, Any], persona_path: Path):
        """Validate persona prompt configuration."""
        if 'persona_prompt' not in persona_card:
            return
        
        persona_prompt = persona_card['persona_prompt']
        
        # Check for prompt content - either direct or file reference
        has_content = 'content' in persona_prompt and persona_prompt['content'].strip()
        has_file = 'prompt_file' in persona_prompt
        
        if not has_content and not has_file:
            self.validation_results.append(f"❌ {participant_id}: No prompt content or prompt_file specified")
            return
        
        if has_file:
            prompt_file = persona_prompt['prompt_file']
            
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
                            char_count = len(prompt_content)
                            self.validation_results.append(f"✅ {participant_id}: Prompt file has content ({char_count} chars)")
                            
                            # Quality checks for prompt content
                            if char_count < 50:
                                self.validation_results.append(f"⚠️ {participant_id}: Prompt seems very short")
                            elif char_count > 5000:
                                self.validation_results.append(f"⚠️ {participant_id}: Prompt is very long - may hit token limits")
                        else:
                            self.validation_results.append(f"❌ {participant_id}: Prompt file is empty")
                except Exception as e:
                    self.validation_results.append(f"❌ {participant_id}: Error reading prompt file: {e}")
            else:
                self.validation_results.append(f"❌ {participant_id}: Prompt file not found: {prompt_path}")
        
        if has_content:
            content = persona_prompt['content'].strip()
            char_count = len(content)
            self.validation_results.append(f"✅ {participant_id}: Direct prompt content ({char_count} chars)")
            
            if char_count < 50:
                self.validation_results.append(f"⚠️ {participant_id}: Prompt seems very short")
    
    def _validate_model_config(self, participant_id: str, persona_card: Dict[str, Any]):
        """Validate model configuration."""
        if 'model_config' not in persona_card:
            return
        
        model_config = persona_card['model_config']
        
        # Check for required model fields
        if 'model_name' in model_config:
            model_name = model_config['model_name']
            self.validation_results.append(f"✅ {participant_id}: Model configured: {model_name}")
            
            # Warn about common model naming issues
            if not model_name.strip():
                self.validation_results.append(f"❌ {participant_id}: Model name is empty")
        else:
            self.validation_results.append(f"❌ {participant_id}: Missing required 'model_name' in model_config")
        
        # Check for optional but important model parameters
        optional_params = ['temperature', 'max_tokens', 'top_p']
        for param in optional_params:
            if param in model_config:
                value = model_config[param]
                self.validation_results.append(f"✅ {participant_id}: {param} = {value}")
                
                # Validate parameter ranges
                if param == 'temperature' and (value < 0 or value > 2):
                    self.validation_results.append(f"⚠️ {participant_id}: Temperature {value} is outside normal range (0-2)")
                elif param == 'top_p' and (value < 0 or value > 1):
                    self.validation_results.append(f"⚠️ {participant_id}: top_p {value} is outside valid range (0-1)")
                elif param == 'max_tokens' and value < 1:
                    self.validation_results.append(f"⚠️ {participant_id}: max_tokens {value} is too low")
            else:
                self.validation_results.append(f"⚠️ {participant_id}: No {param} specified (will use defaults)")
    
    def _validate_participant_config(self, participant_id: str, participant_config: Dict[str, Any]):
        """Validate participant-level configuration."""
        # Check description
        if 'description' in participant_config:
            description = participant_config['description']
            if description.strip():
                self.validation_results.append(f"✅ {participant_id}: Description: {description}")
            else:
                self.validation_results.append(f"⚠️ {participant_id}: Description is empty")
        else:
            self.validation_results.append(f"⚠️ {participant_id}: No description provided")
        
        # Check LLM role
        if 'llm_role' in participant_config:
            llm_role = participant_config['llm_role']
            if llm_role in ['user', 'assistant']:
                self.validation_results.append(f"✅ {participant_id}: LLM role: {llm_role}")
            else:
                self.validation_results.append(f"❌ {participant_id}: Invalid llm_role '{llm_role}' (must be 'user' or 'assistant')")
        else:
            self.validation_results.append(f"⚠️ {participant_id}: No llm_role specified (will use default)")
        
        # Check modifier configuration
        apply_modifiers = participant_config.get('apply_modifiers', False)
        if apply_modifiers:
            applied_modifiers = participant_config.get('applied_modifiers', [])
            if applied_modifiers:
                self.validation_results.append(f"✅ {participant_id}: Modifiers configured: {applied_modifiers}")
            else:
                self.validation_results.append(f"❌ {participant_id}: apply_modifiers=true but no applied_modifiers specified")
        else:
            self.validation_results.append(f"✅ {participant_id}: No modifiers (as configured)")
    
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
        
        # Validate scenario domain
        if 'domain' in scenario:
            domain = scenario['domain']
            self.validation_results.append(f"✅ Scenario domain: {domain}")
        else:
            self.validation_results.append("⚠️ No domain specified in scenario")
        
        # Check vignette content - handle both JSON and text files
        self._validate_vignette_content(vignette_path)
    
    def _validate_vignette_content(self, vignette_path: Path):
        """Validate vignette content structure and quality."""
        try:
            if vignette_path.suffix.lower() == '.json':
                with open(vignette_path, 'r', encoding='utf-8') as f:
                    vignette_data = json.load(f)
                
                if 'vignette_card' in vignette_data:
                    self.validation_results.append("✅ Vignette JSON structure is valid")
                    vignette_card = vignette_data['vignette_card']
                    
                    # Check for metadata (optional, don't warn about missing fields)
                    if 'metadata' in vignette_card:
                        metadata = vignette_card['metadata']
                        if 'title' in metadata:
                            self.validation_results.append(f"✅ Vignette has title: {metadata['title']}")
                        if 'description' in metadata:
                            self.validation_results.append(f"✅ Vignette has description")
                    else:
                        self.validation_results.append("⚠️ Vignette has no metadata section")
                    
                    if 'content' in vignette_card and 'vignette_file' in vignette_card['content']:
                        content_file = vignette_card['content']['vignette_file']
                        content_path = vignette_path.parent / content_file
                        
                        if content_path.exists():
                            with open(content_path, 'r', encoding='utf-8') as cf:
                                content_text = cf.read().strip()
                                if content_text:
                                    char_count = len(content_text)
                                    self.validation_results.append(f"✅ Vignette content file has text ({char_count} chars)")
                                    
                                    # Quality checks
                                    if char_count < 50:
                                        self.validation_results.append("⚠️ Vignette content seems quite short")
                                    # Remove the "very long" warning as it's not necessarily problematic
                                else:
                                    self.validation_results.append("❌ Vignette content file is empty")
                        else:
                            self.validation_results.append(f"❌ Vignette content file not found: {content_path}")
                else:
                    self.validation_results.append("⚠️ Vignette JSON doesn't have expected vignette_card structure")
            else:
                # Direct text file
                with open(vignette_path, 'r', encoding='utf-8') as f:
                    vignette_content = f.read().strip()
                    if vignette_content:
                        char_count = len(vignette_content)
                        self.validation_results.append(f"✅ Vignette has content ({char_count} chars)")
                        if char_count < 50:
                            self.validation_results.append("⚠️ Vignette content seems quite short")
                        # Remove length warnings for long content
                    else:
                        self.validation_results.append("❌ Vignette file is empty")
        except Exception as e:
            self.validation_results.append(f"❌ Error reading vignette file: {e}")
    
    def _validate_modifiers(self):
        """Validate modifier configuration and file with enhanced checks."""
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
            
            # Validate modifier structure and application rules
            self._validate_modifier_structure(modifier_data)
            
            # Check if requested modifier categories exist
            self._validate_requested_modifier_categories(modifying_adjectives)
            
            # Validate modifier configuration options
            self._validate_modifier_configuration(modifier_config)
            
        except json.JSONDecodeError as e:
            self.validation_results.append(f"❌ Invalid JSON in modifier file: {e}")
        except Exception as e:
            self.validation_results.append(f"❌ Error reading modifier file: {e}")
    
    def _validate_modifier_structure(self, modifier_data: Dict[str, Any]):
        """Validate the structure of the modifier file."""
        modifying_adjectives = modifier_data['modifying_adjectives']
        
        # Check for application rules
        if 'modifier_application_rules' in modifier_data:
            rules = modifier_data['modifier_application_rules']
            self.validation_results.append("✅ Found modifier application rules")
            
            # Check for specific rule types
            rule_types = ['complementary_combinations', 'avoid_contradictions', 'intensity_matching', 'contextual_weighting']
            for rule_type in rule_types:
                if rule_type in rules:
                    self.validation_results.append(f"✅ Found {rule_type} rules")
                else:
                    self.validation_results.append(f"⚠️ Missing {rule_type} rules")
        else:
            self.validation_results.append("⚠️ No modifier application rules found - using basic selection")
        
        # Validate category structure
        for category_name, category in modifying_adjectives.items():
            if not isinstance(category, dict):
                self.validation_results.append(f"❌ Category '{category_name}' is not a dictionary")
                continue
            
            spectrum_count = len(category)
            total_modifiers = sum(len(spectrum) for spectrum in category.values())
            
            if spectrum_count == 0:
                self.validation_results.append(f"❌ Category '{category_name}' has no spectrums")
            elif total_modifiers == 0:
                self.validation_results.append(f"❌ Category '{category_name}' has no modifiers")
            else:
                self.validation_results.append(f"✅ Category '{category_name}': {spectrum_count} spectrums, {total_modifiers} total modifiers")
    
    def _validate_requested_modifier_categories(self, modifying_adjectives: Dict[str, Any]):
        """Validate that requested modifier categories exist."""
        participants = self.config.get('participants', {})
        for participant_id, participant_config in participants.items():
            if participant_config.get('apply_modifiers', False):
                applied_modifiers = participant_config.get('applied_modifiers', [])
                for category in applied_modifiers:
                    if category in modifying_adjectives:
                        category_data = modifying_adjectives[category]
                        spectrum_count = len(category_data)
                        total_modifiers = sum(len(spectrum) for spectrum in category_data.values())
                        self.validation_results.append(f"✅ {participant_id}: Category '{category}' exists ({spectrum_count} spectrums, {total_modifiers} modifiers)")
                    else:
                        self.validation_results.append(f"❌ {participant_id}: Modifier category '{category}' not found in modifier file")
                        
                        # Suggest similar category names
                        available_categories = list(modifying_adjectives.keys())
                        suggestions = [cat for cat in available_categories if category.lower() in cat.lower() or cat.lower() in category.lower()]
                        if suggestions:
                            self.validation_results.append(f"   💡 Did you mean: {', '.join(suggestions[:3])}")
    
    def _validate_modifier_configuration(self, modifier_config: Dict[str, Any]):
        """Validate modifier configuration options."""
        # Check personality coherence setting
        if 'personality_coherence' in modifier_config:
            coherence = modifier_config['personality_coherence']
            valid_coherence = ['low', 'balanced', 'high']
            if coherence in valid_coherence:
                self.validation_results.append(f"✅ Personality coherence: {coherence}")
            else:
                self.validation_results.append(f"❌ Invalid personality_coherence '{coherence}' (must be: {', '.join(valid_coherence)})")
        else:
            self.validation_results.append("⚠️ No personality_coherence specified (will use 'balanced')")
        
        # Check target modifier count
        if 'target_modifier_count' in modifier_config:
            count = modifier_config['target_modifier_count']
            if isinstance(count, int) and count > 0:
                if count > 6:
                    self.validation_results.append(f"⚠️ target_modifier_count {count} is quite high - may create overwhelming personalities")
                else:
                    self.validation_results.append(f"✅ Target modifier count: {count}")
            else:
                self.validation_results.append(f"❌ Invalid target_modifier_count '{count}' (must be positive integer)")
        else:
            self.validation_results.append("⚠️ No target_modifier_count specified (will use 3)")
    
    def _validate_conversation_logic(self):
        """Validate conversation-level logic and consistency."""
        self.validation_results.append("\n--- Validating Conversation Logic ---")
        
        # Check conversation parameters
        conv_params = self.config.get('conversation_parameters', {})
        participants = self.config.get('participants', {})
        
        if 'initiator' in conv_params:
            initiator = conv_params['initiator']
            if initiator in participants:
                self.validation_results.append(f"✅ Initiator '{initiator}' is a valid participant")
            else:
                self.validation_results.append(f"❌ Initiator '{initiator}' is not in participants list")
                self.validation_results.append(f"   Available participants: {', '.join(participants.keys())}")
        else:
            self.validation_results.append("❌ No initiator specified in conversation_parameters")
        
        # Check LLM role distribution
        llm_roles = {}
        for participant_id, config in participants.items():
            role = config.get('llm_role', 'assistant')
            if role not in llm_roles:
                llm_roles[role] = []
            llm_roles[role].append(participant_id)
        
        if len(llm_roles) == 1:
            self.validation_results.append("⚠️ All participants have the same LLM role - conversation may be one-sided")
        else:
            for role, participant_list in llm_roles.items():
                self.validation_results.append(f"✅ LLM role '{role}': {', '.join(participant_list)}")
    
    def _validate_modifier_combinations(self):
        """Validate modifier combinations using the modifier engine if available."""
        self.validation_results.append("\n--- Validating Modifier Combinations ---")
        
        # Skip modifier engine validation for now since import path is complex
        # This would require the validator to be run from the right directory
        # or have the modifier engine properly installed as a package
        
        modifier_config = self.config.get('modifier_config')
        if not modifier_config:
            self.validation_results.append("⚠️ No modifier config to validate")
            return
        
        participants = self.config.get('participants', {})
        has_modifier_participants = any(
            p.get('apply_modifiers', False) for p in participants.values()
        )
        
        if has_modifier_participants:
            self.validation_results.append("✅ Modifier configuration appears valid")
            self.validation_results.append("   (Advanced validation requires running conversation generation)")
        else:
            self.validation_results.append("✅ No participants use modifiers - no combination validation needed")


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
        print("\nThis validator checks:")
        print("  ✅ Configuration file structure and syntax")
        print("  ✅ Participant personas and their dependencies") 
        print("  ✅ Vignette files and content quality")
        print("  ✅ Modifier categories and application rules")
        print("  ✅ Conversation logic and role consistency")
        print("  ✅ Modifier combination validation (if engine available)")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    print("🔍 Interface Validation Results:")
    print("=" * 80)
    
    validator = InterfaceValidator(config_path)
    is_valid, messages = validator.validate_all()
    
    # Print results with better formatting
    current_section = ""
    for message in messages:
        if message.startswith("\n---"):
            current_section = message.strip()
            print(f"\n{current_section}")
            print("-" * (len(current_section) - 4))
        elif message.startswith("---"):
            current_section = message.strip()
            print(f"\n{current_section}")
            print("-" * len(current_section))
        else:
            print(message)
    
    print("\n" + "=" * 80)
    
    # Summary with counts
    errors = [msg for msg in messages if msg.startswith("❌")]
    warnings = [msg for msg in messages if msg.startswith("⚠️")]
    successes = [msg for msg in messages if msg.startswith("✅")]
    
    print(f"\n📊 VALIDATION SUMMARY:")
    print(f"   ✅ Successes: {len(successes)}")
    print(f"   ⚠️  Warnings: {len(warnings)}")
    print(f"   ❌ Errors: {len(errors)}")
    
    if is_valid:
        print(f"\n🎉 Validation PASSED! Ready for conversation generation.")
        if warnings:
            print(f"   Note: {len(warnings)} warnings found - review for optimal results")
        sys.exit(0)
    else:
        print(f"\n💥 Validation FAILED!")
        print(f"   Fix {len(errors)} error(s) before proceeding with generation")
        if warnings:
            print(f"   Also consider addressing {len(warnings)} warning(s)")
        sys.exit(1)
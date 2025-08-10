#!/usr/bin/env python3
"""
Conversation Generator v8

Generates synthetic conversations based on JSON interface files.
Includes interface validation and path checking functionality.
"""

import argparse
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd

from utils.llm_provider import LLMProvider
from utils.modifier_engine import ModifierEngine


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
        
        # Check vignette content
        try:
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


class ConversationGenerator:
    def __init__(self, conversation_config_path: str):
        """Initialize conversation generator with configuration file."""
        self.config_path = conversation_config_path
        self.config = self._load_conversation_config()
        self.llm_provider = LLMProvider()
        self.modifier_engine = ModifierEngine()
        
        # Load all required components
        self.participants = self._load_participants()
        self.vignette_content = self._load_vignette()
        self.applied_modifiers = self._apply_modifiers()
        
    def _load_conversation_config(self) -> Dict[str, Any]:
        """Load the main conversation configuration file."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config['conversation_card']
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Error loading conversation config from {self.config_path}: {e}")
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to config directory."""
        if file_path.startswith('./') or file_path.startswith('../'):
            config_dir = Path(self.config_path).parent
            resolved_path = config_dir / file_path
        else:
            resolved_path = Path(file_path)
        
        return resolved_path.resolve()
    
    def _load_participants(self) -> Dict[str, Dict[str, Any]]:
        """Load persona configurations for all participants."""
        participants = {}
        
        for participant_id, participant_config in self.config['participants'].items():
            persona_file = participant_config['persona_file']
            persona_path = self._resolve_path(persona_file)
            
            try:
                with open(persona_path, 'r', encoding='utf-8') as f:
                    persona_data = json.load(f)
                
                # Load prompt content if specified
                persona_card = persona_data['persona_card']
                if 'prompt_file' in persona_card['persona_prompt']:
                    prompt_file = persona_card['persona_prompt']['prompt_file']
                    
                    # Resolve prompt file path relative to persona file
                    if prompt_file.startswith('./') or prompt_file.startswith('../'):
                        prompt_path = persona_path.parent / prompt_file
                    else:
                        prompt_path = Path(prompt_file)
                    
                    prompt_path = prompt_path.resolve()
                    
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        prompt_content = f.read()
                    
                    persona_card['persona_prompt']['content'] = prompt_content
                
                participants[participant_id] = {
                    'config': participant_config,
                    'persona': persona_card
                }
                
            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                raise ValueError(f"Error loading persona for {participant_id}: {e}")
        
        return participants
    
    def _load_vignette(self) -> str:
        """Load vignette content."""
        vignette_file = self.config['scenario']['vignette_file']
        vignette_path = self._resolve_path(vignette_file)
        
        try:
            with open(vignette_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError as e:
            raise ValueError(f"Error loading vignette from {vignette_path}: {e}")
    
    def _apply_modifiers(self) -> Dict[str, List[str]]:
        """Apply random modifiers to participants who need them."""
        if 'modifier_config' not in self.config:
            return {}
        
        modifier_file = self.config['modifier_config']['modifiers_file']
        modifier_path = self._resolve_path(modifier_file)
        
        applied_modifiers = {}
        
        for participant_id, participant_config in self.config['participants'].items():
            if participant_config.get('apply_modifiers', False):
                modifier_categories = participant_config.get('applied_modifiers', [])
                
                participant_modifiers = self.modifier_engine.generate_random_modifiers(
                    str(modifier_path), modifier_categories
                )
                applied_modifiers[participant_id] = participant_modifiers
            else:
                applied_modifiers[participant_id] = []
        
        return applied_modifiers
    
    def _build_system_prompt(self, participant_id: str) -> str:
        """Build the complete system prompt for a participant."""
        participant = self.participants[participant_id]
        base_prompt = participant['persona']['persona_prompt']['content']
        
        # Add vignette context
        full_prompt = f"{self.vignette_content}\n\n{base_prompt}"
        
        # Add modifiers if any
        modifiers = self.applied_modifiers.get(participant_id, [])
        if modifiers:
            modifier_text = f"\n\nAdditional behavioral modifiers for this conversation: {', '.join(modifiers)}"
            full_prompt += modifier_text
        
        return full_prompt
    
    def _get_model_config(self, participant_id: str) -> Dict[str, Any]:
        """Get model configuration for a participant."""
        return self.participants[participant_id]['persona']['model_config']
    
    def generate_single_conversation(self, num_turns: int) -> List[Dict[str, Any]]:
        """Generate a single conversation with specified number of turns."""
        conversation = []
        initiator = self.config['conversation_parameters']['initiator']
        
        # Set up participants
        participant_ids = list(self.participants.keys())
        if initiator not in participant_ids:
            raise ValueError(f"Initiator '{initiator}' not found in participants")
        
        # Arrange turn order starting with initiator
        other_participant = [p for p in participant_ids if p != initiator][0]
        turn_order = [initiator, other_participant]
        
        # Build system prompts
        system_prompts = {}
        for participant_id in participant_ids:
            system_prompts[participant_id] = self._build_system_prompt(participant_id)
        
        # Initialize conversation history for each participant
        conversation_history = {pid: [] for pid in participant_ids}
        
        # Generate conversation turns
        for turn in range(num_turns):
            current_participant = turn_order[turn % len(turn_order)]
            other_participant = turn_order[(turn + 1) % len(turn_order)]
            
            # Build messages for current participant
            messages = [{"role": "system", "content": system_prompts[current_participant]}]
            messages.extend(conversation_history[current_participant])
            
            # Get model config
            model_config = self._get_model_config(current_participant)
            
            # Generate response
            response = self.llm_provider.generate_completion(
                messages=messages,
                model_config=model_config
            )
            
            # Record the turn
            turn_data = {
                'turn': turn,
                'participant': current_participant,
                'role': 'assistant' if turn % 2 == 0 else 'user',  # Alternating roles
                'content': response,
                'modifiers': self.applied_modifiers.get(current_participant, [])
            }
            conversation.append(turn_data)
            
            # Update conversation history for both participants
            conversation_history[current_participant].append({
                "role": "assistant", 
                "content": response
            })
            conversation_history[other_participant].append({
                "role": "user", 
                "content": response
            })
        
        return conversation
    
    def generate_conversations(self, num_turns: int, num_conversations: int) -> List[List[Dict[str, Any]]]:
        """Generate multiple conversations."""
        conversations = []
        
        for i in range(num_conversations):
            print(f"Generating conversation {i + 1}/{num_conversations}...")
            
            # Re-apply random modifiers for each conversation to prevent topic collapse
            self.applied_modifiers = self._apply_modifiers()
            
            conversation = self.generate_single_conversation(num_turns)
            conversations.append(conversation)
        
        return conversations
    
    def save_conversations_csv(self, conversations: List[List[Dict[str, Any]]], output_dir: str):
        """Save conversations to CSV files using pandas."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, conversation in enumerate(conversations):
            filename = f"conversation_{timestamp}_{i+1:03d}.csv"
            filepath = os.path.join(output_dir, filename)
            
            # Convert conversation to DataFrame
            df = pd.DataFrame(conversation)
            
            # Convert modifiers list to string for CSV
            df['modifiers'] = df['modifiers'].apply(lambda x: ', '.join(x) if x else '')
            
            # Save to CSV
            df.to_csv(filepath, index=False, encoding='utf-8')
            
            print(f"Saved conversation to {filepath}")
    
    def save_conversations_json(self, conversations: List[List[Dict[str, Any]]], output_dir: str):
        """Save conversations to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversations_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        output_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "config_file": self.config_path,
                "conversation_title": self.config['title'],
                "total_conversations": len(conversations),
                "turns_per_conversation": len(conversations[0]) if conversations else 0
            },
            "conversations": conversations
        }
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(conversations)} conversations to {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic conversations from JSON interface files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check interfaces without generating
  python gen_conversations_v8.py --config conversation.json --check-interfaces
  
  # Generate conversations
  python gen_conversations_v8.py --config conversation.json --turns 10 --count 5 --output-dir outputs/test_run
  
  # Check and generate if valid
  python gen_conversations_v8.py -c conversation.json -t 8 -n 3 --output-dir outputs/experiment --format json
        """
    )
    
    parser.add_argument(
        "-c", "--config", 
        required=True,
        help="Path to conversation JSON configuration file"
    )
    
    parser.add_argument(
        "--check-interfaces", 
        action="store_true",
        help="Validate interface files without generating conversations"
    )
    
    parser.add_argument(
        "-t", "--turns", 
        type=int, 
        default=5,
        help="Number of turns per conversation (default: 5)"
    )
    
    parser.add_argument(
        "-n", "--count", 
        type=int, 
        default=1,
        help="Number of conversations to generate (default: 1)"
    )
    
    parser.add_argument(
        "--format", 
        choices=["csv", "json", "both"], 
        default="csv",
        help="Output format (default: csv)"
    )
    
    parser.add_argument(
        "--output-dir", 
        help="Output directory for generated conversations (required unless using --check-interfaces)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.check_interfaces and not args.output_dir:
        parser.error("--output-dir is required unless using --check-interfaces")
    
    try:
        # Always run interface validation first
        print("🔍 Validating conversation interfaces...")
        print("=" * 60)
        
        validator = InterfaceValidator(args.config)
        is_valid, messages = validator.validate_all()
        
        # Print validation results
        for message in messages:
            print(message)
        
        print("=" * 60)
        
        # If only checking interfaces, exit here
        if args.check_interfaces:
            if is_valid:
                print("🎉 Interface validation passed!")
                return 0
            else:
                print("💥 Interface validation failed!")
                return 1
        
        # If validation failed, don't proceed with generation
        if not is_valid:
            print("💥 Cannot proceed with conversation generation due to interface validation errors.")
            print("Run with --check-interfaces to see detailed validation results.")
            return 1
        
        print("✅ Interface validation passed! Proceeding with conversation generation...\n")
        
        # Initialize generator
        generator = ConversationGenerator(args.config)
        
        # Generate conversations
        conversations = generator.generate_conversations(args.turns, args.count)
        
        # Save in requested format(s)
        if args.format in ["csv", "both"]:
            generator.save_conversations_csv(conversations, args.output_dir)
        
        if args.format in ["json", "both"]:
            generator.save_conversations_json(conversations, args.output_dir)
        
        print(f"\n🎉 Successfully generated {len(conversations)} conversations with {args.turns} turns each.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
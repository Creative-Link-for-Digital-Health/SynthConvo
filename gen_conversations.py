#!/usr/bin/env python3
"""
Conversation Generator v9 - Role Flexible & Clean

Generates synthetic conversations with complete role flexibility.
Works for any training scenario: client simulation, worker training, etc.
Uses modular design with separate validation library.
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
from utils.interface_validator import InterfaceValidator


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
        """Load vignette content - handles both JSON vignette cards and direct text files."""
        vignette_file = self.config['scenario']['vignette_file']
        vignette_path = self._resolve_path(vignette_file)
        
        try:
            # Check if it's a JSON vignette card or direct text content
            if vignette_path.suffix.lower() == '.json':
                # Load vignette card and extract content file path
                with open(vignette_path, 'r', encoding='utf-8') as f:
                    vignette_data = json.load(f)
                
                if 'vignette_card' in vignette_data:
                    vignette_card = vignette_data['vignette_card']
                    
                    if 'content' in vignette_card and 'vignette_file' in vignette_card['content']:
                        content_file = vignette_card['content']['vignette_file']
                        
                        # Resolve content file path relative to vignette file
                        if content_file.startswith('./') or content_file.startswith('../'):
                            content_path = vignette_path.parent / content_file
                        else:
                            content_path = Path(content_file)
                        
                        content_path = content_path.resolve()
                        
                        with open(content_path, 'r', encoding='utf-8') as cf:
                            return cf.read()
                    else:
                        raise ValueError("Vignette JSON missing content structure")
                else:
                    # If no vignette_card structure, treat as direct JSON content
                    return json.dumps(vignette_data, indent=2)
            else:
                # Direct text file
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
    
    def _build_system_prompt_with_modifiers(self, participant_id: str, conversation_modifiers: Dict[str, List[str]]) -> str:
        """Build the complete system prompt for a participant with specific modifiers."""
        participant = self.participants[participant_id]
        base_prompt = participant['persona']['persona_prompt']['content']
        
        # Add vignette context
        full_prompt = f"{self.vignette_content}\n\n{base_prompt}"
        
        # Add conversation-specific modifiers if any
        modifiers = conversation_modifiers.get(participant_id, [])
        if modifiers:
            modifier_text = f"\n\nAdditional behavioral modifiers for this conversation: {', '.join(modifiers)}"
            full_prompt += modifier_text
        
        return full_prompt
    
    def _get_model_config(self, participant_id: str) -> Dict[str, Any]:
        """Get model configuration for a participant."""
        return self.participants[participant_id]['persona']['model_config']
    
    def generate_conversations(self, num_turns: int, num_conversations: int) -> List[List[Dict[str, Any]]]:
        """Generate multiple conversations with role flexibility."""
        conversations = []
        
        for i in range(num_conversations):
            print(f"Generating conversation {i + 1}/{num_conversations}...")
            
            # Generate single conversation
            conversation = self._generate_single_conversation(num_turns)
            conversations.append(conversation)
        
        return conversations
    
    def _generate_single_conversation(self, num_turns: int) -> List[Dict[str, Any]]:
        """Generate a single conversation with pre-applied modifiers and flexible roles."""
        conversation = []
        initiator = self.config['conversation_parameters']['initiator']
        
        # Set up participants
        participant_ids = list(self.participants.keys())
        if initiator not in participant_ids:
            raise ValueError(f"Initiator '{initiator}' not found in participants")
        
        # Arrange turn order starting with initiator
        other_participant = [p for p in participant_ids if p != initiator][0]
        turn_order = [initiator, other_participant]
        
        # Apply modifiers and build system prompts ONCE per conversation
        conversation_modifiers = self._apply_modifiers()
        system_prompts = {}
        for participant_id in participant_ids:
            system_prompts[participant_id] = self._build_system_prompt_with_modifiers(participant_id, conversation_modifiers)
        
        # Track the full conversation flow for proper context
        full_conversation_history = []
        
        # Generate conversation turns (each turn is a complete Q&A exchange)
        for turn in range(num_turns):
            turn_responses = []
            
            # Generate both parts of the exchange for this turn
            for exchange_part in range(2):  # Question, then Answer
                current_participant = turn_order[exchange_part % len(turn_order)]
                other_participant_id = turn_order[(exchange_part + 1) % len(turn_order)]
                
                # Get participant configuration
                participant_config = self.config['participants'][current_participant]
                llm_role = participant_config.get('llm_role', 'assistant')
                
                # Build messages for current participant (system prompt + history)
                messages = [{"role": "system", "content": system_prompts[current_participant]}]
                
                # Add the conversation history from the current participant's perspective with speaker names
                for i, historical_msg in enumerate(full_conversation_history):
                    hist_participant = historical_msg['participant']
                    hist_content = historical_msg['content']
                    
                    # Get the speaker name for this message
                    hist_participant_config = self.config['participants'][hist_participant]
                    speaker_name = hist_participant_config.get('description', hist_participant)
                    
                    # Prefix content with speaker name
                    prefixed_content = f"{speaker_name}: {hist_content}"
                    
                    if hist_participant == current_participant:
                        # This participant's own messages
                        messages.append({"role": llm_role, "content": prefixed_content})
                    else:
                        # Other participant's messages (opposite role)
                        other_role = "user" if llm_role == "assistant" else "assistant"
                        messages.append({"role": other_role, "content": prefixed_content})
                
                # Add conversation starter for the very first exchange
                if turn == 0 and exchange_part == 0:
                    messages.append({
                        "role": "user", 
                        "content": "Begin the conversation now."
                    })
                elif exchange_part == 0 and turn > 0:
                    # For subsequent questions from the worker, give them context
                    messages.append({
                        "role": "user",
                        "content": "Continue the conversation by asking an appropriate follow-up question based on what was just said."
                    })
                
                # Get model config
                model_config = self._get_model_config(current_participant)
                
                # Generate response
                try:
                    response = self.llm_provider.generate_completion(
                        messages=messages,
                        model_config=model_config
                    )
                    
                    # Ensure we got a response
                    if not response or not response.strip():
                        response = f"[{participant_config.get('description', current_participant)} would respond here]"
                        print(f"Warning: Empty response from {current_participant}, using placeholder")
                        
                except Exception as e:
                    response = f"[Error generating response: {e}]"
                    print(f"Error generating response for {current_participant}: {e}")
                
                # Record the response as part of this turn
                turn_data = {
                    'turn': turn,
                    'participant': current_participant,
                    'role': llm_role,
                    'content': response.strip(),
                    'modifiers': conversation_modifiers.get(current_participant, [])
                }
                turn_responses.append(turn_data)
                
                # Add to full conversation history
                full_conversation_history.append({
                    'participant': current_participant,
                    'content': response.strip()
                })
            
            # Add both parts of this turn to the conversation
            conversation.extend(turn_responses)
        
        return conversation
    
    def save_conversations_json(self, conversations: List[List[Dict[str, Any]]], output_dir: str, debug_prompts: bool = False):
        """Save conversations to JSON files using the improved schema."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, conversation in enumerate(conversations):
            filename = f"conversation_{timestamp}_{i+1:03d}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Convert to new JSON schema
            conversation_json = self._convert_to_json_schema(conversation, i+1)
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(conversation_json, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Saved conversation to {filepath}")
            
            # Save debug prompt information if requested
            if debug_prompts:
                self._save_debug_prompts(conversation, i+1, output_dir, timestamp)
    
    def _convert_to_json_schema(self, conversation: List[Dict[str, Any]], conversation_num: int) -> Dict[str, Any]:
        """Convert internal conversation format to the structured JSON schema."""
        timestamp = datetime.now().isoformat() + "Z"
        conversation_id = f"conv_{conversation_num:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract persona information
        personas = {}
        initial_system_prompts = {}
        
        for participant_id, participant_data in self.participants.items():
            participant_config = self.config['participants'][participant_id]
            persona_card = participant_data['persona']
            
            # Get persona name from config or generate from participant_id
            persona_name = participant_config.get('description', participant_id.replace('_', ' ').title())
            
            personas[participant_id] = {
                "name": persona_name,
                "llm_role": participant_config.get('llm_role', 'assistant'),
                "persona": persona_card['persona_prompt'].get('role', persona_name)
            }
            
            # Build system prompt (clean version for documentation)
            base_prompt = persona_card['persona_prompt']['content']
            full_system_prompt = f"{self.vignette_content}\n\n{base_prompt}"
            
            initial_system_prompts[participant_id] = {
                "system_prompt": full_system_prompt
            }
        
        # Group conversation messages by turns
        conversation_turns = []
        current_turn = None
        current_turn_number = -1
        
        for msg in conversation:
            turn_number = msg['turn']
            participant = msg['participant']
            role = msg['role']
            content = msg['content']
            
            # Start new turn if needed
            if turn_number != current_turn_number:
                if current_turn is not None:
                    conversation_turns.append(current_turn)
                
                current_turn = {
                    "turn_number": turn_number + 1,  # 1-indexed for display
                    "exchanges": []
                }
                current_turn_number = turn_number
            
            # Add exchange to current turn
            exchange = {
                "role": role,
                "name": personas[participant]["name"],
                "participant_id": participant,
                "message": {
                    "content": content
                },
                "modifiers": msg['modifiers'] if msg['modifiers'] else []
            }
            
            current_turn["exchanges"].append(exchange)
        
        # Add the last turn
        if current_turn is not None:
            conversation_turns.append(current_turn)
        
        # Build final JSON structure
        conversation_json = {
            "conversation_id": conversation_id,
            "title": self.config.get('title', 'Generated Conversation'),
            "description": self.config.get('metadata', {}).get('description', 'Synthetic conversation generated from personas'),
            "created_timestamp": timestamp,
            "total_turns": len(conversation_turns),
            "domain": self.config.get('scenario', {}).get('domain', 'general'),
            "personas": personas,
            "initial_system_prompts": initial_system_prompts,
            "conversation_turns": conversation_turns,
            "metadata": {
                "config_file": self.config_path,
                "generation_timestamp": timestamp,
                "vignette_file": self.config.get('scenario', {}).get('vignette_file', ''),
                "modifier_config": self.config.get('modifier_config', {}),
                "conversation_parameters": self.config.get('conversation_parameters', {})
            }
        }
        
        return conversation_json
    
    def _save_debug_prompts(self, conversation: List[Dict[str, Any]], conversation_num: int, output_dir: str, timestamp: str):
        """Save detailed prompt debugging information."""
        # Recreate the conversation modifiers from the first turn
        conversation_modifiers = {}
        for turn_data in conversation:
            participant = turn_data['participant']
            if participant not in conversation_modifiers:
                conversation_modifiers[participant] = turn_data['modifiers']
        
        # Save detailed prompt information for each participant
        for participant_id in self.participants.keys():
            debug_filename = f"conversation_{timestamp}_{conversation_num:03d}_{participant_id}_debug.txt"
            debug_filepath = os.path.join(output_dir, debug_filename)
            
            with open(debug_filepath, 'w', encoding='utf-8') as f:
                f.write(f"=== DEBUG PROMPT INFORMATION FOR {participant_id.upper()} ===\n\n")
                
                # 1. Show the complete system prompt with modifiers
                system_prompt = self._build_system_prompt_with_modifiers(participant_id, conversation_modifiers)
                f.write(f"1. COMPLETE SYSTEM PROMPT (with modifiers):\n")
                f.write("=" * 60 + "\n")
                f.write(system_prompt)
                f.write("\n" + "=" * 60 + "\n\n")
                
                # 2. Show participant configuration
                participant_config = self.config['participants'][participant_id]
                f.write(f"2. PARTICIPANT CONFIGURATION:\n")
                f.write("=" * 40 + "\n")
                f.write(f"Description: {participant_config.get('description', 'N/A')}\n")
                f.write(f"LLM Role: {participant_config.get('llm_role', 'N/A')}\n")
                f.write(f"Apply Modifiers: {participant_config.get('apply_modifiers', False)}\n")
                f.write(f"Applied Modifiers: {conversation_modifiers.get(participant_id, [])}\n")
                f.write("\n")
                
                # 3. Show how conversation history builds up for this participant
                f.write(f"3. CONVERSATION HISTORY FROM {participant_id.upper()}'S PERSPECTIVE:\n")
                f.write("=" * 50 + "\n")
                
                # Simulate the conversation history building
                full_conversation_history = []
                llm_role = participant_config.get('llm_role', 'assistant')
                
                f.write(f"This participant has LLM role: {llm_role}\n")
                f.write(f"So they see:\n")
                f.write(f"- Their own messages as: {llm_role}\n")
                f.write(f"- Other participant's messages as: {'user' if llm_role == 'assistant' else 'assistant'}\n\n")
                
                turn_count = 0
                for turn_data in conversation:
                    turn_count += 1
                    hist_participant = turn_data['participant']
                    hist_content = turn_data['content']
                    
                    # Add to simulated history
                    full_conversation_history.append({
                        'participant': hist_participant,
                        'content': hist_content
                    })
                    
                    f.write(f"--- After Turn {turn_count} ---\n")
                    f.write(f"Latest message from: {hist_participant}\n")
                    f.write(f"Content: {hist_content[:100]}{'...' if len(hist_content) > 100 else ''}\n")
                    
                    # Show what this participant would see at this point
                    f.write(f"\nComplete message history that {participant_id} would see:\n")
                    
                    # Build the message history from this participant's perspective
                    messages = [{"role": "system", "content": "[SYSTEM PROMPT SHOWN ABOVE]"}]
                    
                    for i, historical_msg in enumerate(full_conversation_history):
                        hist_p = historical_msg['participant']
                        hist_c = historical_msg['content']
                        
                        if hist_p == participant_id:
                            # This participant's own messages
                            role = llm_role
                            speaker_name = participant_config.get('description', participant_id)
                        else:
                            # Other participant's messages (opposite role)
                            role = "user" if llm_role == "assistant" else "assistant"
                            other_participant_config = self.config['participants'][hist_p]
                            speaker_name = other_participant_config.get('description', hist_p)
                        
                        # Show with speaker prefix
                        prefixed_content = f"{speaker_name}: {hist_c}"
                        f.write(f"  Message {i+1}: role='{role}', content='{prefixed_content[:80]}{'...' if len(prefixed_content) > 80 else ''}'\n")
                        messages.append({"role": role, "content": prefixed_content})
                    
                    f.write(f"\nMessage sequence: {[m['role'] for m in messages[1:]]}\n")  # Skip system message
                    f.write("\n" + "-" * 40 + "\n\n")
                
                # 4. Show the exact API call for the last exchange
                f.write(f"4. FINAL API CALL EXAMPLE (last exchange):\n")
                f.write("=" * 40 + "\n")
                f.write("messages = [\n")
                f.write("  {\n")
                f.write("    \"role\": \"system\",\n")
                # Fix the f-string backslash issue
                system_preview = system_prompt[:100].replace('\n', '\\n')
                f.write(f"    \"content\": \"{system_preview}...\"\n")
                f.write("  },\n")
                
                # Show last few messages
                if len(messages) > 1:
                    for msg in messages[-3:]:  # Show last 3 messages
                        f.write("  {\n")
                        f.write(f"    \"role\": \"{msg['role']}\",\n")
                        # Fix the f-string backslash issue
                        content_preview = msg['content'][:100].replace('\n', '\\n').replace('"', '\\"')
                        content_preview = content_preview + ('...' if len(msg['content']) > 100 else '')
                        f.write(f"    \"content\": \"{content_preview}\"\n")
                        f.write("  },\n")
                
                f.write("]\n\n")
                f.write("=" * 60 + "\n")
            
            print(f"Saved debug info for {participant_id} to {debug_filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic conversations from JSON interface files - Role Flexible",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check interfaces without generating
  python gen_conversations_v9.py --config conversation.json --check-interfaces
  
  # Generate conversations for client simulation training
  python gen_conversations_v9.py --config conversation.json --turns 5 --count 3 --output-dir outputs/client_training
  
  # Generate with debug prompt information
  python gen_conversations_v9.py --config conversation.json --turns 3 --count 1 --output-dir outputs/debug --debug-prompts
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
        "--debug-prompts", 
        action="store_true",
        help="Save detailed prompt information to separate files for debugging"
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
        
        # Save as JSON with debug info if requested
        generator.save_conversations_json(conversations, args.output_dir, args.debug_prompts)
        
        print(f"\n🎉 Successfully generated {len(conversations)} conversations with {args.turns} turns each.")
        print(f"💾 Output saved to: {args.output_dir}")
        
        if args.debug_prompts:
            print(f"🔍 Debug prompt files saved with detailed conversation history analysis")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
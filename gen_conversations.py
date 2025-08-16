#!/usr/bin/env python3
"""
Generate synthetic conversations

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
import copy

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
        """Apply intelligent modifiers to participants who need them."""
        if 'modifier_config' not in self.config:
            return {}
        
        modifier_file = self.config['modifier_config']['modifiers_file']
        modifier_path = self._resolve_path(modifier_file)
        
        # Get context type for intelligent modifier selection
        context_type = self.config.get('scenario', {}).get('domain', 'general')
        
        # Get coherence level from config (default: balanced)
        coherence_level = self.config['modifier_config'].get('personality_coherence', 'balanced')
        
        # Get target modifier count from config (default: 3)
        target_count = self.config['modifier_config'].get('target_modifier_count', 3)
        
        applied_modifiers = {}
        
        for participant_id, participant_config in self.config['participants'].items():
            if participant_config.get('apply_modifiers', False):
                modifier_categories = participant_config.get('applied_modifiers', [])
                
                # Use the new smart modifier generation
                participant_modifiers = self.modifier_engine.generate_smart_modifiers(
                    modifier_file_path=str(modifier_path),
                    requested_categories=modifier_categories,
                    context_type=context_type,
                    personality_coherence=coherence_level,
                    target_count=target_count
                )
                
                # Validate the generated combination and log results
                validation = self.modifier_engine.validate_modifier_combination(participant_modifiers)
                if not validation.get('is_valid', True):
                    print(f"⚠️  Modifier validation warning for {participant_id}:")
                    for suggestion in validation.get('suggestions', []):
                        print(f"   - {suggestion}")
                    if validation.get('conflicting_pairs'):
                        print(f"   - Conflicting pairs: {validation['conflicting_pairs']}")
                
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
            modifier_text = (
                f"\n\nThere are a number of feelings and behavioral tendencies that you currently have about this situation. "
                f"Given your personality and what's happening, here are the specific traits you should try very hard to embody "
                f"throughout this conversation: {', '.join(modifiers)}"
            )
            full_prompt += modifier_text
        
        return full_prompt
    
    def _get_model_config(self, participant_id: str) -> Dict[str, Any]:
        """Get model configuration for a participant."""
        return self.participants[participant_id]['persona']['model_config']
    
    def _get_speaker_name(self, participant_id: str) -> str:
        """Get the display name for a participant."""
        return self.config['participants'][participant_id].get('description', participant_id)
    
    def _build_message_history(self, full_conversation_history: List[Dict[str, str]], 
                              current_participant: str, system_prompt: str) -> List[Dict[str, str]]:
        """Build message history for a participant from their perspective."""
        participant_config = self.config['participants'][current_participant]
        llm_role = participant_config.get('llm_role', 'assistant')
        
        # Start with system prompt
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add the conversation history from the current participant's perspective with speaker names
        for historical_msg in full_conversation_history:
            hist_participant = historical_msg['participant']
            hist_content = historical_msg['content']
            
            # Get the speaker name for this message
            speaker_name = self._get_speaker_name(hist_participant)
            
            # Prefix content with speaker name
            prefixed_content = f"{speaker_name}: {hist_content}"
            
            if hist_participant == current_participant:
                # This participant's own messages
                messages.append({"role": llm_role, "content": prefixed_content})
            else:
                # Other participant's messages (opposite role)
                other_role = "user" if llm_role == "assistant" else "assistant"
                messages.append({"role": other_role, "content": prefixed_content})
        
        return messages
    
    def generate_conversations(self, num_turns: int, num_conversations: int, 
                             capture_debug: bool = False) -> List[Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]]:
        """Generate multiple conversations with role flexibility."""
        conversations = []
        
        for i in range(num_conversations):
            print(f"Generating conversation {i + 1}/{num_conversations}...")
            
            # Generate single conversation
            conversation, debug_data = self._generate_single_conversation(num_turns, capture_debug)
            conversations.append((conversation, debug_data))
        
        return conversations
    
    def _generate_single_conversation(self, num_turns: int, capture_debug: bool = False) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
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
        
        # Initialize debug data if requested
        debug_data = None
        if capture_debug:
            debug_data = {
                'conversation_modifiers': copy.deepcopy(conversation_modifiers),
                'system_prompts': copy.deepcopy(system_prompts),
                'turn_snapshots': [],  # Capture exact state at each turn
                'message_history_snapshots': [],  # Capture message history progression
                'generation_metadata': {
                    'initiator': initiator,
                    'turn_order': turn_order,
                    'participant_configs': {pid: self.config['participants'][pid] for pid in participant_ids}
                }
            }
        
        # Track the full conversation flow for proper context
        full_conversation_history = []
        
        # Generate conversation turns (each turn is a complete Q&A exchange)
        for turn in range(num_turns):
            turn_responses = []
            turn_debug_info = {
                'turn_number': turn,
                'exchanges': []
            } if capture_debug else None
            
            # Generate both parts of the exchange for this turn
            for exchange_part in range(2):  # Question, then Answer
                current_participant = turn_order[exchange_part % len(turn_order)]
                other_participant_id = turn_order[(exchange_part + 1) % len(turn_order)]
                
                # Get participant configuration
                participant_config = self.config['participants'][current_participant]
                llm_role = participant_config.get('llm_role', 'assistant')
                
                # Build messages for current participant using shared logic
                messages = self._build_message_history(
                    full_conversation_history, 
                    current_participant, 
                    system_prompts[current_participant]
                )
                
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
                
                # Capture debug info for this exchange BEFORE API call
                if capture_debug:
                    exchange_debug = {
                        'exchange_part': exchange_part,
                        'current_participant': current_participant,
                        'llm_role': llm_role,
                        'messages_sent_to_llm': copy.deepcopy(messages),  # Exact messages sent
                        'conversation_history_length': len(full_conversation_history),
                        'system_prompt_used': system_prompts[current_participant]
                    }
                
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
                
                # Complete debug info for this exchange
                if capture_debug:
                    exchange_debug.update({
                        'response_received': response.strip(),
                        'model_config_used': copy.deepcopy(model_config),
                        'generation_timestamp': datetime.now().isoformat()
                    })
                    turn_debug_info['exchanges'].append(exchange_debug)
                
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
                
                # Capture message history snapshot after this exchange
                if capture_debug:
                    debug_data['message_history_snapshots'].append({
                        'after_turn': turn,
                        'after_exchange': exchange_part,
                        'participant': current_participant,
                        'full_history_state': copy.deepcopy(full_conversation_history),
                        'message_count': len(full_conversation_history)
                    })
            
            # Add turn debug info
            if capture_debug and turn_debug_info:
                debug_data['turn_snapshots'].append(turn_debug_info)
            
            # Add both parts of this turn to the conversation
            conversation.extend(turn_responses)
        
        return conversation, debug_data
    
    def save_conversations_json(self, conversations: List[Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]], 
                               output_dir: str, save_debug: bool = False):
        """Save conversations to JSON files using the improved schema."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, (conversation, debug_data) in enumerate(conversations):
            filename = f"conversation_{timestamp}_{i+1:03d}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Convert to new JSON schema
            conversation_json = self._convert_to_json_schema(conversation, i+1)
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(conversation_json, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Saved conversation to {filepath}")
            
            # Save debug information if requested and available
            if save_debug and debug_data:
                self._save_debug_data(debug_data, conversation, i+1, output_dir, timestamp)
    
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
    
    def _save_debug_data(self, debug_data: Dict[str, Any], conversation: List[Dict[str, Any]], 
                        conversation_num: int, output_dir: str, timestamp: str):
        """Save comprehensive debug information captured during generation."""
        
        # Save raw debug data as JSON
        debug_json_filename = f"conversation_{timestamp}_{conversation_num:03d}_debug_data.json"
        debug_json_filepath = os.path.join(output_dir, debug_json_filename)
        
        with open(debug_json_filepath, 'w', encoding='utf-8') as f:
            json.dump(debug_data, f, indent=2, ensure_ascii=False)
        print(f"Saved raw debug data to {debug_json_filepath}")
        
        # Save modifier validation report
        self._save_modifier_validation_report(debug_data, conversation_num, output_dir, timestamp)
        
        # Save human-readable debug analysis for each participant
        for participant_id in debug_data['generation_metadata']['participant_configs'].keys():
            debug_filename = f"conversation_{timestamp}_{conversation_num:03d}_{participant_id}_debug_analysis.txt"
            debug_filepath = os.path.join(output_dir, debug_filename)
            
            with open(debug_filepath, 'w', encoding='utf-8') as f:
                self._write_debug_analysis(f, debug_data, participant_id, conversation)
            
            print(f"Saved debug analysis for {participant_id} to {debug_filepath}")
    
    def _save_modifier_validation_report(self, debug_data: Dict[str, Any], conversation_num: int, 
                                       output_dir: str, timestamp: str):
        """Save detailed modifier validation and selection report."""
        validation_filename = f"conversation_{timestamp}_{conversation_num:03d}_modifier_report.txt"
        validation_filepath = os.path.join(output_dir, validation_filename)
        
        with open(validation_filepath, 'w', encoding='utf-8') as f:
            f.write("=== MODIFIER SELECTION AND VALIDATION REPORT ===\n\n")
            
            conversation_modifiers = debug_data.get('conversation_modifiers', {})
            
            for participant_id, modifiers in conversation_modifiers.items():
                f.write(f"PARTICIPANT: {participant_id.upper()}\n")
                f.write("=" * 50 + "\n")
                
                if not modifiers:
                    f.write("No modifiers applied to this participant.\n\n")
                    continue
                
                f.write(f"Applied Modifiers: {modifiers}\n\n")
                
                # Validate this combination
                validation = self.modifier_engine.validate_modifier_combination(modifiers)
                
                f.write("VALIDATION RESULTS:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Overall Valid: {validation.get('is_valid', 'Unknown')}\n")
                f.write(f"Has Contradictions: {validation.get('has_contradictions', 'Unknown')}\n")
                f.write(f"Intensity Coherent: {validation.get('intensity_coherent', 'Unknown')}\n")
                f.write(f"Category Diversity: {validation.get('category_diversity', 'Unknown')}\n")
                f.write(f"Intensity Levels: {validation.get('intensity_levels', [])}\n")
                f.write(f"Represented Categories: {validation.get('represented_categories', [])}\n")
                
                if validation.get('conflicting_pairs'):
                    f.write(f"\nCONFLICTING PAIRS:\n")
                    for pair in validation['conflicting_pairs']:
                        f.write(f"  - {pair[0]} ↔ {pair[1]}\n")
                
                if validation.get('suggestions'):
                    f.write(f"\nSUGGESTIONS FOR IMPROVEMENT:\n")
                    for suggestion in validation['suggestions']:
                        f.write(f"  - {suggestion}\n")
                
                f.write("\n" + "=" * 70 + "\n\n")
        
        print(f"Saved modifier validation report to {validation_filepath}")
    
    def _write_debug_analysis(self, f, debug_data: Dict[str, Any], participant_id: str, conversation: List[Dict[str, Any]]):
        """Write comprehensive debug analysis for a specific participant."""
        f.write(f"=== COMPREHENSIVE DEBUG ANALYSIS FOR {participant_id.upper()} ===\n\n")
        
        # 1. Generation Overview
        f.write("1. GENERATION OVERVIEW\n")
        f.write("=" * 50 + "\n")
        metadata = debug_data['generation_metadata']
        participant_config = metadata['participant_configs'][participant_id]
        f.write(f"Initiator: {metadata['initiator']}\n")
        f.write(f"Turn order: {metadata['turn_order']}\n")
        f.write(f"Participant role: {participant_config.get('llm_role', 'assistant')}\n")
        f.write(f"Applied modifiers: {debug_data['conversation_modifiers'].get(participant_id, [])}\n")
        f.write(f"Total turns generated: {len(debug_data['turn_snapshots'])}\n\n")
        
        # 2. Modifier Analysis
        modifiers = debug_data['conversation_modifiers'].get(participant_id, [])
        if modifiers:
            f.write("2. MODIFIER ANALYSIS\n")
            f.write("=" * 50 + "\n")
            
            # Validate modifiers
            validation = self.modifier_engine.validate_modifier_combination(modifiers)
            
            f.write(f"Selected Modifiers: {modifiers}\n")
            f.write(f"Modifier Count: {len(modifiers)}\n")
            f.write(f"Valid Combination: {validation.get('is_valid', 'Unknown')}\n")
            f.write(f"Intensity Levels: {validation.get('intensity_levels', [])}\n")
            f.write(f"Category Diversity: {validation.get('category_diversity', 0)}\n")
            f.write(f"Represented Categories: {validation.get('represented_categories', [])}\n")
            
            if validation.get('conflicting_pairs'):
                f.write(f"⚠️  Conflicting Pairs: {validation['conflicting_pairs']}\n")
            
            if validation.get('suggestions'):
                f.write(f"Improvement Suggestions:\n")
                for suggestion in validation['suggestions']:
                    f.write(f"  - {suggestion}\n")
            
            f.write(f"\nModifier Integration in Prompt:\n")
            f.write(f"\"There are a number of feelings and behavioral tendencies that you currently have about this situation. ")
            f.write(f"Given your personality and what's happening, here are the specific traits you should try very hard to embody ")
            f.write(f"throughout this conversation: {', '.join(modifiers)}\"\n\n")
        else:
            f.write("2. MODIFIER ANALYSIS\n")
            f.write("=" * 50 + "\n")
            f.write("No modifiers applied to this participant.\n\n")
        
        # 3. System Prompt Used
        f.write("3. EXACT SYSTEM PROMPT USED\n")
        f.write("=" * 50 + "\n")
        system_prompt = debug_data['system_prompts'][participant_id]
        f.write(system_prompt)
        f.write("\n\n")
        
        # 4. Turn-by-turn Analysis
        f.write("4. TURN-BY-TURN GENERATION ANALYSIS\n")
        f.write("=" * 50 + "\n")
        
        for turn_snapshot in debug_data['turn_snapshots']:
            turn_num = turn_snapshot['turn_number']
            f.write(f"\n--- TURN {turn_num + 1} ---\n")
            
            for exchange in turn_snapshot['exchanges']:
                if exchange['current_participant'] == participant_id:
                    f.write(f"\nEXCHANGE: {participant_id} (Exchange Part {exchange['exchange_part']})\n")
                    f.write(f"LLM Role: {exchange['llm_role']}\n")
                    f.write(f"Conversation History Length: {exchange['conversation_history_length']}\n")
                    f.write(f"Generation Time: {exchange['generation_timestamp']}\n")
                    
                    f.write(f"\nExact Messages Sent to LLM:\n")
                    for i, msg in enumerate(exchange['messages_sent_to_llm']):
                        role = msg['role']
                        content = msg['content']
                        if role == 'system':
                            f.write(f"  [{i}] SYSTEM: [System prompt - see section 3]\n")
                        else:
                            content_preview = content[:100] + ('...' if len(content) > 100 else '')
                            f.write(f"  [{i}] {role.upper()}: {content_preview}\n")
                    
                    f.write(f"\nResponse Generated:\n")
                    response_preview = exchange['response_received'][:200] + ('...' if len(exchange['response_received']) > 200 else '')
                    f.write(f"  {response_preview}\n")
                    
                    f.write(f"\nModel Config Used:\n")
                    for key, value in exchange['model_config_used'].items():
                        f.write(f"  {key}: {value}\n")
        
        # 5. Message History Progression
        f.write(f"\n\n5. MESSAGE HISTORY PROGRESSION FOR {participant_id.upper()}\n")
        f.write("=" * 60 + "\n")
        f.write("This shows how the conversation history grew from this participant's perspective:\n\n")
        
        participant_config = metadata['participant_configs'][participant_id]
        llm_role = participant_config.get('llm_role', 'assistant')
        
        for snapshot in debug_data['message_history_snapshots']:
            if snapshot['participant'] == participant_id:
                f.write(f"After Turn {snapshot['after_turn'] + 1}, Exchange {snapshot['after_exchange'] + 1}:\n")
                f.write(f"History length: {snapshot['message_count']} messages\n")
                
                # Show how this participant would see the conversation at this point
                f.write("Message sequence this participant sees:\n")
                messages = self._build_message_history(
                    snapshot['full_history_state'], 
                    participant_id, 
                    "[SYSTEM PROMPT]"
                )
                
                for i, msg in enumerate(messages):
                    if i == 0:  # System message
                        f.write(f"  [{i}] system: [SYSTEM PROMPT]\n")
                    else:
                        role = msg['role']
                        content = msg['content'][:80] + ('...' if len(msg['content']) > 80 else '')
                        f.write(f"  [{i}] {role}: {content}\n")
                
                f.write(f"Role sequence: {[m['role'] for m in messages[1:]]}\n")  # Skip system
                f.write("-" * 40 + "\n")
        
        # 6. Final State Summary
        f.write(f"\n\n6. FINAL STATE SUMMARY\n")
        f.write("=" * 40 + "\n")
        final_snapshot = debug_data['message_history_snapshots'][-1] if debug_data['message_history_snapshots'] else None
        if final_snapshot:
            f.write(f"Final conversation length: {final_snapshot['message_count']} exchanges\n")
            
            # Count this participant's messages
            participant_messages = [msg for msg in final_snapshot['full_history_state'] if msg['participant'] == participant_id]
            f.write(f"Messages from {participant_id}: {len(participant_messages)}\n")
            
            # Show final message roles
            final_messages = self._build_message_history(
                final_snapshot['full_history_state'], 
                participant_id, 
                "[SYSTEM]"
            )
            f.write(f"Final role sequence: {[m['role'] for m in final_messages]}\n")
        
        f.write("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic conversations from JSON interface files - Role Flexible",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check interfaces without generating
  python gen_conversations.py --config conversation.json --check-interfaces
  
  # Generate conversations for client simulation training
  python gen_conversations.py --config conversation.json --turns 5 --count 3 --output-dir outputs/client_training
  
  # Generate with debug information
  python gen_conversations.py --config conversation.json --turns 3 --count 1 --output-dir outputs/debug --debug
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
        "--debug", 
        action="store_true",
        help="Capture and save comprehensive debug information during generation"
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
        
        # Generate conversations with debug capture if requested
        conversations = generator.generate_conversations(args.turns, args.count, args.debug)
        
        # Save as JSON with debug info if captured
        generator.save_conversations_json(conversations, args.output_dir, args.debug)
        
        print(f"\n🎉 Successfully generated {len(conversations)} conversations with {args.turns} turns each.")
        print(f"💾 Output saved to: {args.output_dir}")
        
        if args.debug:
            print(f"🔍 Comprehensive debug information saved:")
            print(f"   - Raw debug data (JSON format)")
            print(f"   - Modifier validation reports")
            print(f"   - Per-participant analysis (human-readable)")
            print(f"   - Exact API call history and message progression")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
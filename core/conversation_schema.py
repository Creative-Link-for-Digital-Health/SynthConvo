"""
Conversation schema and JSON output formatting.

Handles conversion from internal conversation format to structured JSON output
and manages the final conversation data schema.
"""

import json
import os
import copy
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class ConversationSchema:
    """Handles conversion to JSON schema and file output."""
    
    def __init__(self, config: Dict[str, Any], participants: Dict[str, Dict[str, Any]], config_path: str):
        """Initialize with conversation config and participant data."""
        self.config = config
        self.participants = participants
        self.config_path = config_path
    
    def convert_to_json_schema(self, conversation: List[Dict[str, Any]], 
                             conversation_num: int, conversation_modifiers: Dict[str, List[str]],
                             actual_system_prompts: Dict[str, str]) -> Dict[str, Any]:
        """Convert internal conversation format to the structured JSON schema."""
        timestamp = datetime.now().isoformat() + "Z"
        conversation_id = f"conv_{conversation_num:03d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract persona information with modifiers reported once
        personas = self._build_personas_section(conversation_modifiers)
        
        # Build initial system prompts section using actual prompts from generation
        initial_system_prompts = {}
        for participant_id, system_prompt in actual_system_prompts.items():
            initial_system_prompts[participant_id] = {
                "system_prompt": system_prompt
            }
        
        # Group conversation messages by turns
        conversation_turns = self._build_conversation_turns(conversation, personas)
        
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
            "metadata": self._build_metadata_section(timestamp)
        }
        
        return conversation_json
    
    def _build_personas_section(self, conversation_modifiers: Dict[str, List[str]]) -> Dict[str, Any]:
        """Build the personas section with modifiers reported once per conversation."""
        personas = {}
        initiator = self.config['conversation_parameters']['initiator']
        
        for participant_id, participant_data in self.participants.items():
            participant_config = self.config['participants'][participant_id]
            persona_card = participant_data['persona']
            
            # Get persona name from config or generate from participant_id
            persona_name = participant_config.get('description', participant_id.replace('_', ' ').title())
            
            # Determine role based on initiator status (simplified for JSON output)
            is_initiator = participant_id == initiator
            conversation_role = "initiator" if is_initiator else "responder"
            display_role = "user" if is_initiator else "assistant"  # For display purposes
            
            personas[participant_id] = {
                "name": persona_name,
                "role": display_role,  # For display in JSON
                "conversation_role": conversation_role,
                "persona": persona_card['persona_prompt'].get('role', persona_name),
                "modifiers": conversation_modifiers.get(participant_id, [])
            }
        
        return personas
    
    def _build_initial_system_prompts_section(self, conversation_modifiers: Dict[str, List[str]]) -> Dict[str, Any]:
        """Build the initial system prompts section using the actual prompts from generation."""
        # We'll pass in the actual system prompts from the conversation generator
        # rather than rebuilding them here
        return {}  # This will be populated by the calling function
    
    def _build_conversation_turns(self, conversation: List[Dict[str, Any]], personas: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Group conversation messages by turns with XML role tags."""
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
            
            # Get participant name for XML tag
            participant_name = personas[participant]["name"]
            
            # Add XML role tag to content
            tagged_content = f"<{participant_name} />{content}"
            
            # Add exchange to current turn with XML role tagging
            exchange = {
                "role": role,
                "name": participant_name,
                "participant_id": participant,
                "message": {
                    "content": tagged_content
                }
            }
            
            current_turn["exchanges"].append(exchange)
        
        # Add the last turn
        if current_turn is not None:
            conversation_turns.append(current_turn)
        
        return conversation_turns
    
    def _build_metadata_section(self, timestamp: str) -> Dict[str, Any]:
        """Build the metadata section."""
        return {
            "config_file": self.config_path,
            "generation_timestamp": timestamp,
            "vignette_file": self.config.get('scenario', {}).get('vignette_file', ''),
            "modifier_config": self.config.get('modifier_config', {}),
            "conversation_parameters": self.config.get('conversation_parameters', {})
        }
    
    def save_conversations_json(self, conversations: List[Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]], 
                               output_dir: str, save_debug: bool = False):
        """Save conversations to JSON files using the improved schema."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for i, (conversation, debug_data) in enumerate(conversations):
            filename = f"conversation_{timestamp}_{i+1:03d}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Apply modifiers to get them for the schema
            from utils.modifier_engine import ModifierEngine
            modifier_engine = ModifierEngine()
            conversation_modifiers = self._apply_modifiers_for_schema(modifier_engine)
            
            # Get actual system prompts from debug data if available
            actual_system_prompts = {}
            if debug_data and 'system_prompts' in debug_data:
                actual_system_prompts = debug_data['system_prompts']
            
            # Convert to new JSON schema with actual system prompts
            conversation_json = self.convert_to_json_schema(conversation, i+1, conversation_modifiers, actual_system_prompts)
            
            with open(filepath, 'w', encoding='utf-8') as jsonfile:
                json.dump(conversation_json, jsonfile, indent=2, ensure_ascii=False)
            
            print(f"Saved conversation to {filepath}")
            
            # Only save debug JSON if requested (no text files)
            if save_debug and debug_data:
                debug_json_filename = f"conversation_{timestamp}_{i+1:03d}_debug_data.json"
                debug_json_filepath = os.path.join(output_dir, debug_json_filename)
                
                with open(debug_json_filepath, 'w', encoding='utf-8') as f:
                    json.dump(debug_data, f, indent=2, ensure_ascii=False)
                print(f"Saved debug data to {debug_json_filepath}")
    
    def _apply_modifiers_for_schema(self, modifier_engine) -> Dict[str, List[str]]:
        """Apply modifiers specifically for schema generation."""
        if 'modifier_config' not in self.config:
            return {}
        
        from pathlib import Path
        
        # Resolve modifier file path
        modifier_file = self.config['modifier_config']['modifiers_file']
        if modifier_file.startswith('./') or modifier_file.startswith('../'):
            config_dir = Path(self.config_path).parent
            modifier_path = config_dir / modifier_file
        else:
            modifier_path = Path(modifier_file)
        
        # Get modifier generation parameters
        context_type = self.config.get('scenario', {}).get('domain', 'general')
        coherence_level = self.config['modifier_config'].get('personality_coherence', 'balanced')
        target_count = self.config['modifier_config'].get('target_modifier_count', 3)
        
        applied_modifiers = {}
        
        for participant_id, participant_config in self.config['participants'].items():
            if participant_config.get('apply_modifiers', False):
                modifier_categories = participant_config.get('applied_modifiers', [])
                
                # Generate modifiers for this participant
                participant_modifiers = modifier_engine.generate_smart_modifiers(
                    modifier_file_path=str(modifier_path),
                    requested_categories=modifier_categories,
                    context_type=context_type,
                    personality_coherence=coherence_level,
                    target_count=target_count
                )
                
                applied_modifiers[participant_id] = participant_modifiers
            else:
                applied_modifiers[participant_id] = []
        
        return applied_modifiers
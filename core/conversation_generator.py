"""
Core conversation generator.

Main orchestration logic for generating synthetic conversations with role flexibility.
"""

import copy
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from utils.llm_provider import LLMProvider
from utils.modifier_engine import ModifierEngine
from utils.file_loader import FileLoader
from .system_prompt_builder import SystemPromptBuilder
from .conversation_schema import ConversationSchema


class ConversationGenerator:
    """Main conversation generator that orchestrates the entire process."""
    
    def __init__(self, conversation_config_path: str):
        """Initialize conversation generator with configuration file."""
        self.config_path = conversation_config_path
        
        # Initialize components
        self.file_loader = FileLoader(conversation_config_path)
        self.llm_provider = LLMProvider()
        self.modifier_engine = ModifierEngine()
        
        # Load configuration and content
        self.config = self.file_loader.load_conversation_config()
        self.participants = self.file_loader.load_participants(self.config)
        self.vignette_content = self.file_loader.load_vignette(self.config)
        
        # Initialize builders
        self.prompt_builder = SystemPromptBuilder(self.config, self.participants, self.vignette_content)
        self.schema_handler = ConversationSchema(self.config, self.participants, self.config_path)
    
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
            system_prompts[participant_id] = self.prompt_builder.build_system_prompt(participant_id, conversation_modifiers)
        
        # Initialize debug data if requested
        debug_data = None
        if capture_debug:
            debug_data = {
                'conversation_modifiers': copy.deepcopy(conversation_modifiers),
                'system_prompts': copy.deepcopy(system_prompts),
                'turn_snapshots': [],
                'message_history_snapshots': [],
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
                
                # Determine role based on initiator status
                initiator = self.config['conversation_parameters']['initiator']
                is_initiator = current_participant == initiator
                
                # For conversation generation, both participants act as assistants
                # but we track their logical roles for message history building
                determined_role = "assistant"  # Both generate as assistants
                
                # Build messages for current participant
                messages = self.prompt_builder.build_message_history(
                    full_conversation_history, 
                    current_participant, 
                    system_prompts[current_participant]
                )
                
                # Capture debug info for this exchange BEFORE API call
                if capture_debug:
                    exchange_debug = {
                        'exchange_part': exchange_part,
                        'current_participant': current_participant,
                        'determined_role': determined_role,
                        'is_initiator': is_initiator,
                        'messages_sent_to_llm': copy.deepcopy(messages),
                        'conversation_history_length': len(full_conversation_history),
                        'system_prompt_used': system_prompts[current_participant]
                    }
                
                # Get model config
                model_config = self._get_model_config(current_participant)
                
                # Generate response
                try:
                    # Debug: Log the messages being sent
                    print(f"Generating response for {current_participant} (role: {determined_role}, initiator: {is_initiator})")
                    print(f"Messages being sent: {len(messages)} messages")
                    if messages:
                        print(f"Last message role: {messages[-1]['role']}")
                        print(f"Last message content preview: {messages[-1]['content'][:100]}...")
                    
                    response = self.llm_provider.generate_completion(
                        messages=messages,
                        model_config=model_config
                    )
                    
                    print(f"Response received: {response[:100]}...")
                    
                    # Ensure we got a response and it's not a placeholder
                    if (not response or not response.strip() or 
                        ("[" in response and "would respond here]" in response) or
                        ("SOCIAL SERVICES WORKER" in response and "would respond" in response)):
                        
                        print(f"❌ Invalid response detected from {current_participant}")
                        response = f"I need to think about how to respond appropriately to this situation."
                        
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
                    'role': determined_role,
                    'content': response.strip()
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
    
    def _apply_modifiers(self) -> Dict[str, List[str]]:
        """Apply intelligent modifiers to participants who need them."""
        if 'modifier_config' not in self.config:
            return {}
        
        modifier_file = self.config['modifier_config']['modifiers_file']
        modifier_path = self._resolve_modifier_path(modifier_file)
        
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
                
                # Use the modifier engine to generate smart modifiers
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
    
    def _resolve_modifier_path(self, modifier_file: str) -> Path:
        """Resolve modifier file path relative to config directory."""
        if modifier_file.startswith('./') or modifier_file.startswith('../'):
            config_dir = Path(self.config_path).parent
            modifier_path = config_dir / modifier_file
        else:
            modifier_path = Path(modifier_file)
        
        return modifier_path.resolve()
    
    def _get_model_config(self, participant_id: str) -> Dict[str, Any]:
        """Get model configuration for a participant."""
        return self.participants[participant_id]['persona']['model_config']
    
    def save_conversations_json(self, conversations: List[Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]], 
                               output_dir: str, save_debug: bool = False):
        """Save conversations to JSON files using the schema handler."""
        self.schema_handler.save_conversations_json(conversations, output_dir, save_debug)
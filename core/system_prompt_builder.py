"""
System prompt builder for conversation generation.

Handles role-based prompt construction, modifier integration,
and conversation behavior instructions.
"""

from typing import Dict, List, Any


class SystemPromptBuilder:
    """Builds system prompts with role-based behavior and modifier integration."""
    
    def __init__(self, config: Dict[str, Any], participants: Dict[str, Dict[str, Any]], vignette_content: str):
        """Initialize with conversation config, participant data, and vignette content."""
        self.config = config
        self.participants = participants
        self.vignette_content = vignette_content
    
    def build_system_prompt(self, participant_id: str, conversation_modifiers: Dict[str, List[str]]) -> str:
        """Build the complete system prompt for a participant with role-specific behavior."""
        participant = self.participants[participant_id]
        base_prompt = participant['persona']['persona_prompt']['content']
        
        # Build integrated system prompt with role-specific behavior
        full_prompt = f"{self.vignette_content}\n\n{base_prompt}\n\n"
        
        # Add role-specific conversation behavior
        role_behavior = self._get_role_specific_behavior(participant_id, conversation_modifiers)
        full_prompt += role_behavior
        
        return full_prompt
    
    def _get_role_specific_behavior(self, participant_id: str, conversation_modifiers: Dict[str, List[str]]) -> str:
        """Generate role-specific conversation behavior instructions."""
        participant_config = self.config['participants'][participant_id]
        initiator = self.config['conversation_parameters']['initiator']
        
        # Get conversation role from config or infer from initiator
        conversation_role = participant_config.get('conversation_role')
        if not conversation_role:
            conversation_role = 'initiator' if participant_id == initiator else 'responder'
        
        # Build role-specific behavior instruction
        behavior_instruction = self._build_base_behavior_instruction(conversation_role)
        
        # Add custom behavior from config if available
        custom_behavior = participant_config.get('conversation_behavior')
        if custom_behavior:
            behavior_instruction += f"\n\nSPECIFIC GUIDANCE:\n{custom_behavior}"
        
        # Add modifier instructions if any
        modifiers = conversation_modifiers.get(participant_id, [])
        if modifiers:
            modifier_instruction = self._build_modifier_instruction(modifiers)
            behavior_instruction += modifier_instruction
        
        return behavior_instruction
    
    def _build_base_behavior_instruction(self, conversation_role: str) -> str:
        """Build the base conversation behavior instruction based on role."""
        if conversation_role == 'initiator':
            return (
                "CONVERSATION BEHAVIOR:\n"
                "You are beginning this interaction. Start the conversation naturally based on your role, "
                "personality, and the current situation. Engage authentically according to your character."
            )
        else:
            return (
                "CONVERSATION BEHAVIOR:\n"
                "You will be responding in this interaction. React naturally to what others say, "
                "staying true to your character and the situation. Engage authentically based on your role."
            )
    
    def _build_modifier_instruction(self, modifiers: List[str]) -> str:
        """Build the modifier instruction section."""
        return (
            f"\n\nCURRENT EMOTIONAL/BEHAVIORAL STATE:\n"
            f"You are currently experiencing these feelings and behavioral tendencies that influence "
            f"how you interact: {', '.join(modifiers)}. Let these naturally shape your responses "
            f"while staying true to your core personality."
        )
    
    def needs_initiation_trigger(self, participant_id: str, conversation_history: List[Dict[str, str]]) -> bool:
        """Check if this participant needs an initiation trigger."""
        # Only the very first message of the conversation needs a trigger
        if conversation_history:
            return False
        
        # Check if this participant is configured to start the conversation
        initiator = self.config['conversation_parameters']['initiator']
        return participant_id == initiator
    
    def get_initiation_message(self) -> Dict[str, str]:
        """Get the initiation message for conversation start."""
        return {
            "role": "user", 
            "content": "Begin your interaction now, staying true to your character and the situation."
        }
    
    def get_speaker_name(self, participant_id: str) -> str:
        """Get the display name for a participant."""
        return self.config['participants'][participant_id].get('description', participant_id)
    
    def build_message_history(self, full_conversation_history: List[Dict[str, str]], 
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
            speaker_name = self.get_speaker_name(hist_participant)
            
            # Prefix content with speaker name
            prefixed_content = f"{speaker_name}: {hist_content}"
            
            if hist_participant == current_participant:
                # This participant's own messages
                messages.append({"role": llm_role, "content": prefixed_content})
            else:
                # Other participant's messages (opposite role)
                other_role = "user" if llm_role == "assistant" else "assistant"
                messages.append({"role": other_role, "content": prefixed_content})
        
        # Add initiation trigger only if needed (first message from initiator)
        if self.needs_initiation_trigger(current_participant, full_conversation_history):
            messages.append(self.get_initiation_message())
        
        return messages
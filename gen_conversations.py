#!/usr/bin/env python3
"""
Advanced Conversation Generator

Generates synthetic conversations based on JSON interface files.
Supports persona cards, vignettes, modifiers, and flexible conversation parameters.
"""

import argparse
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import pandas as pd

from utils.llm_provider import LLMProvider
from utils.modifier_engine import ModifierEngine


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
    
    def _load_participants(self) -> Dict[str, Dict[str, Any]]:
        """Load persona configurations for all participants."""
        participants = {}
        
        for participant_id, participant_config in self.config['participants'].items():
            persona_file = participant_config['persona_file']
            
            # Resolve relative path from conversation config directory
            config_dir = Path(self.config_path).parent
            persona_path = config_dir / persona_file
            
            try:
                with open(persona_path, 'r', encoding='utf-8') as f:
                    persona_data = json.load(f)
                
                # Load prompt content if specified
                persona_card = persona_data['persona_card']
                if 'prompt_file' in persona_card['persona_prompt']:
                    prompt_file = persona_card['persona_prompt']['prompt_file']
                    prompt_path = persona_path.parent / prompt_file
                    
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
        
        # Resolve relative path from conversation config directory
        config_dir = Path(self.config_path).parent
        vignette_path = config_dir / vignette_file
        
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
        
        # Resolve relative path from conversation config directory
        config_dir = Path(self.config_path).parent
        modifier_path = config_dir / modifier_file
        
        applied_modifiers = {}
        
        for participant_id, participant_config in self.config['participants'].items():
            if participant_config.get('apply_modifiers', False):
                modifier_categories = participant_config.get('applied_modifiers', [])
                
                participant_modifiers = self.modifier_engine.generate_random_modifiers(
                    modifier_path, modifier_categories
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
    
    def save_conversations_csv(self, conversations: List[List[Dict[str, Any]]], output_dir: str = "outputs/conversation_datasets"):
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
    
    def save_conversations_json(self, conversations: List[List[Dict[str, Any]]], output_dir: str = "outputs/conversation_datasets"):
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
        epilog=        """
Examples:
  python gen_conversations_v2.py --config ./input_libraries/conversations/conversation_001.example.json --turns 10 --count 5 --output-dir outputs/test_run
  python gen_conversations_v2.py -c ./path/to/conversation.json -t 8 -n 3 --format json --output-dir outputs/experiment_1
        """
    )
    
    parser.add_argument(
        "-c", "--config", 
        required=True,
        help="Path to conversation JSON configuration file"
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
        required=True,
        help="Output directory for generated conversations"
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize generator
        generator = ConversationGenerator(args.config)
        
        # Generate conversations
        conversations = generator.generate_conversations(args.turns, args.count)
        
        # Save in requested format(s)
        if args.format in ["csv", "both"]:
            generator.save_conversations_csv(conversations, args.output_dir)
        
        if args.format in ["json", "both"]:
            generator.save_conversations_json(conversations, args.output_dir)
        
        print(f"\nSuccessfully generated {len(conversations)} conversations with {args.turns} turns each.")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
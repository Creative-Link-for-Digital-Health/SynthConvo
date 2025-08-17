#!/usr/bin/env python3
"""
Conversation Extractor Utility

Extracts clean dialog from conversation JSON files for expert review.
Removes technical metadata and presents conversations in standard dialog format.
"""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any


class ConversationExtractor:
    """Extracts and formats conversations for expert review."""
    
    def __init__(self):
        self.conversation_data = None
    
    def load_conversation(self, file_path: str) -> Dict[str, Any]:
        """Load conversation from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.conversation_data = json.load(f)
            return self.conversation_data
        except (FileNotFoundError, json.JSONDecodeError) as e:
            raise ValueError(f"Error loading conversation file: {e}")
    
    def extract_dialog(self, format_type: str = "standard") -> str:
        """Extract dialog in specified format."""
        if not self.conversation_data:
            raise ValueError("No conversation data loaded. Call load_conversation() first.")
        
        if format_type == "standard":
            return self._format_standard_dialog()
        elif format_type == "clinical":
            return self._format_clinical_dialog()
        elif format_type == "screenplay":
            return self._format_screenplay_dialog()
        else:
            raise ValueError(f"Unknown format type: {format_type}")
    
    def _format_standard_dialog(self) -> str:
        """Format as standard dialog with speaker names."""
        output = []
        
        # Add header information
        title = self.conversation_data.get('title', 'Conversation')
        domain = self.conversation_data.get('domain', 'Unknown')
        created = self.conversation_data.get('created_timestamp', 'Unknown')[:10]  # Just date
        
        output.append(f"=== {title} ===")
        output.append(f"Domain: {domain}")
        output.append(f"Date: {created}")
        output.append(f"Total Turns: {self.conversation_data.get('total_turns', 'Unknown')}")
        output.append("")
        
        # Add participant information
        output.append("PARTICIPANTS:")
        for participant_id, persona in self.conversation_data.get('personas', {}).items():
            name = persona.get('name', participant_id)
            role = persona.get('conversation_role', 'participant')
            modifiers = persona.get('modifiers', [])
            
            output.append(f"  • {name} ({role})")
            if modifiers:
                output.append(f"    Behavioral state: {', '.join(modifiers)}")
        
        output.append("")
        output.append("CONVERSATION:")
        output.append("-" * 50)
        
        # Extract dialog from turns
        for turn in self.conversation_data.get('conversation_turns', []):
            for exchange in turn.get('exchanges', []):
                speaker_name = exchange.get('name', 'Unknown Speaker')
                content = exchange.get('message', {}).get('content', '')
                
                # Clean the content (remove XML tags and speaker prefixes)
                clean_content = self._clean_content(content, speaker_name)
                
                # Format the dialog line
                output.append(f"{speaker_name}: {clean_content}")
        
        output.append("-" * 50)
        return "\n".join(output)
    
    def _format_clinical_dialog(self) -> str:
        """Format for clinical review with additional context."""
        output = []
        
        # Clinical header
        title = self.conversation_data.get('title', 'Clinical Conversation')
        output.append(f"CLINICAL REVIEW: {title}")
        output.append("=" * 60)
        output.append("")
        
        # Assessment context
        output.append("ASSESSMENT CONTEXT:")
        domain = self.conversation_data.get('domain', 'Unknown')
        output.append(f"  Setting: {domain.title()}")
        output.append(f"  Interaction Type: Initial Assessment")
        output.append("")
        
        # Participant roles and states
        output.append("PARTICIPANT ANALYSIS:")
        for participant_id, persona in self.conversation_data.get('personas', {}).items():
            name = persona.get('name', participant_id)
            role = persona.get('conversation_role', 'participant')
            modifiers = persona.get('modifiers', [])
            
            output.append(f"  {name} ({role}):")
            if modifiers:
                output.append(f"    Current state: {', '.join(modifiers)}")
            output.append(f"    Role in interaction: {role}")
            output.append("")
        
        output.append("DIALOG TRANSCRIPT:")
        output.append("-" * 40)
        
        # Add turn numbers and exchange analysis
        for turn in self.conversation_data.get('conversation_turns', []):
            turn_num = turn.get('turn_number', '?')
            output.append(f"\n[TURN {turn_num}]")
            
            for i, exchange in enumerate(turn.get('exchanges', [])):
                speaker_name = exchange.get('name', 'Unknown Speaker')
                content = exchange.get('message', {}).get('content', '')
                
                # Clean the content
                clean_content = self._clean_content(content, speaker_name)
                
                # Add exchange marker
                exchange_type = "Question" if i == 0 else "Response"
                output.append(f"  {exchange_type} - {speaker_name}: {clean_content}")
        
        output.append("\n" + "-" * 40)
        return "\n".join(output)
    
    def _format_screenplay_dialog(self) -> str:
        """Format as screenplay for narrative flow review."""
        output = []
        
        # Screenplay header
        title = self.conversation_data.get('title', 'Conversation')
        output.append(title.upper())
        output.append("")
        output.append("CHARACTERS:")
        
        # Character list
        for participant_id, persona in self.conversation_data.get('personas', {}).items():
            name = persona.get('name', participant_id)
            role = persona.get('conversation_role', 'participant')
            output.append(f"  {name} - {role}")
        
        output.append("")
        output.append("SCENE: Psychiatric unit interview room")
        output.append("")
        
        # Dialog in screenplay format
        for turn in self.conversation_data.get('conversation_turns', []):
            for exchange in turn.get('exchanges', []):
                speaker_name = exchange.get('name', 'Unknown Speaker').upper()
                content = exchange.get('message', {}).get('content', '')
                
                # Clean the content and extract action lines
                clean_content = self._clean_content(content, speaker_name)
                
                # Separate dialog from action descriptions
                lines = clean_content.split('\n')
                dialog_lines = []
                action_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('*') and line.endswith('*'):
                        # Action description
                        action_lines.append(line[1:-1])  # Remove asterisks
                    elif line:
                        dialog_lines.append(line)
                
                # Format for screenplay
                if action_lines:
                    output.append(f"({'; '.join(action_lines)})")
                
                if dialog_lines:
                    output.append(f"{speaker_name}")
                    for line in dialog_lines:
                        if line.strip():
                            output.append(f"    {line}")
                
                output.append("")
        
        return "\n".join(output)
    
    def _clean_content(self, content: str, speaker_name: str) -> str:
        """Clean content by removing XML tags and redundant speaker prefixes."""
        if not content:
            return ""
        
        # Remove XML tags like <SOCIAL SERVICES WORKER />
        content = re.sub(r'<[^>]+\s*/>', '', content)
        
        # Remove speaker prefixes that match the current speaker
        speaker_upper = speaker_name.upper()
        content = re.sub(f'^{re.escape(speaker_upper)}:\\s*', '', content)
        
        # Remove other speaker prefixes that might be embedded
        content = re.sub(r'^[A-Z\s]+:\s*', '', content, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n', '\n', content)
        content = content.strip()
        
        return content
    
    def save_extracted_dialog(self, output_path: str, format_type: str = "standard"):
        """Save extracted dialog to file."""
        dialog = self.extract_dialog(format_type)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(dialog)
        
        print(f"Extracted dialog saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract clean dialog from conversation JSON files for expert review",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Format Options:
  standard   - Clean dialog with speaker names (default)
  clinical   - Clinical review format with analysis context
  screenplay - Screenplay format for narrative flow review

Examples:
  # Extract standard dialog
  python conversation_extractor.py conversation.json

  # Extract clinical format
  python conversation_extractor.py conversation.json --format clinical --output review.txt

  # Extract all conversations in a directory
  python conversation_extractor.py conversations/ --format standard --output-dir extracted/
        """
    )
    
    parser.add_argument(
        "input",
        help="Input conversation JSON file or directory"
    )
    
    parser.add_argument(
        "--format",
        choices=["standard", "clinical", "screenplay"],
        default="standard",
        help="Output format (default: standard)"
    )
    
    parser.add_argument(
        "--output",
        help="Output file path (default: auto-generated)"
    )
    
    parser.add_argument(
        "--output-dir",
        help="Output directory for batch processing"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Process single file
        extractor = ConversationExtractor()
        extractor.load_conversation(str(input_path))
        
        if args.output:
            output_path = args.output
        else:
            # Auto-generate output filename
            stem = input_path.stem
            output_path = f"{stem}_extracted_{args.format}.txt"
        
        extractor.save_extracted_dialog(output_path, args.format)
        
    elif input_path.is_dir():
        # Process directory
        if not args.output_dir:
            args.output_dir = "extracted_dialogs"
        
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        json_files = list(input_path.glob("*.json"))
        
        if not json_files:
            print(f"No JSON files found in {input_path}")
            return
        
        print(f"Processing {len(json_files)} conversation files...")
        
        for json_file in json_files:
            try:
                extractor = ConversationExtractor()
                extractor.load_conversation(str(json_file))
                
                output_name = f"{json_file.stem}_extracted_{args.format}.txt"
                output_path = output_dir / output_name
                
                extractor.save_extracted_dialog(str(output_path), args.format)
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
        
        print(f"Extraction complete. Files saved to: {output_dir}")
    
    else:
        print(f"Error: {input_path} is not a valid file or directory")


if __name__ == "__main__":
    main()
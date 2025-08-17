#!/usr/bin/env python3
"""
Generate synthetic conversations - CLI Entry Point

Simplified command-line interface for conversation generation.
Main logic has been refactored into focused, maintainable components.
"""

import argparse
import sys

from utils.interface_validator import InterfaceValidator
from core.conversation_generator import ConversationGenerator


def main():
    """Main CLI entry point."""
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
    sys.exit(main())
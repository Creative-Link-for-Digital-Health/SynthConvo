#!/usr/bin/env python3
"""
Rewrite the Conversation in a more Natural tone and turn-taking style.
Reads a text file and uses OpenAI API to transform sad content into happy content.
"""

import os
import sys
import argparse
from openai import OpenAI

def read_text_file(file_path):
    """Read content from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)

def transform_text_mood(client, text):
    """Use OpenAI API to transform sad text into happy text."""

    prompt = f"""You are a dialogue rewriter. Your task is to take a structured transcript of a role-play conversation and convert it into a more naturalistic spoken interaction.

    Requirements:

    1. Keep the formatting:

    2. Use the same role labels from the input (SOCIAL SERVICES WORKER:, SOCIAL SERVICES CLIENT:).

    3. Each line should start with the role label followed by the utterance.

    4. Reshape long turns:

        Break up long utterances into multiple shorter turns, as if the speaker pauses, hesitates, or is interrupted.
        Add natural fillers, pauses, and hesitations ("um," "you know," "…") where they fit.
    
    5. Include stage directions:
        Insert parenthetical cues like (shrugs), (sighs), (pauses), (avoids eye contact), (leans forward) to capture body language and awkward silences.

    6. Preserve meaning:
        a. Do not change the actual content of what is being said—only adjust pacing, rhythm, and realism.
        b. Keep the emotional tone consistent with the original.

    7.Do not alter participants: Roles, names, and context must stay the same.

    An example interaction is provided below. Rewrite the dialogue to make it sound more natural and conversational, while adhering to the requirements above.

    Example Interaction Input:
    SOCIAL SERVICES WORKER: "Hi Destiny, thanks for coming in today. My name is Ms. Thompson, and I'll be working with you during our therapy sessions. Please make yourself comfortable over here." (motions to a couch or chair) "Can you tell me a little bit about what's been going on that made you want to come in this week? You mentioned skipping school and feeling frustrated. What's been happening at home or at school that's got you feeling this way?"
    SOCIAL SERVICES CLIENT: (sighs, looking down at phone still in hand) "I don't know... school just feels so pointless most of the time. I'm not really learning anything new, and my teachers are all just like 'you're so capable, Destiny.' But they don't get it. They don't understand why I'm stuck in classes that I hate." (shrugs, eyes flicking up briefly before returning to phone)

    Example Interaction Output:
    SOCIAL SERVICES WORKER: "Hi Destiny, I’m glad you came in today. My name’s Ms. Thompson, and I’ll be working with you in our sessions. You can sit wherever feels comfortable." (waits a moment) "So… um… you mentioned skipping school, and feeling frustrated. Can you tell me a little about what’s been going on?"  
    SOCIAL SERVICES CLIENT: (shrugs, eyes on phone) "I don’t know…" (long pause) "School just feels pointless most of the time."  
    SOCIAL SERVICES WORKER: "Pointless?"  
    SOCIAL SERVICES CLIENT: "Yeah. Like… I’m not learning anything new. Teachers keep saying, ‘you’re so capable, Destiny,’ but…" (quick glance up, then back to phone) "they don’t get it."  

    Here is the text you need to transform:
    {text}
    """

    
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # You can change to "gpt-4" if you prefer
            messages=[
                {"role": "system", "content": "You are a helpful assistant that transforms text to have a more positive, uplifting tone while preserving the original meaning and context."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        sys.exit(1)

def save_transformed_text(original_file_path, transformed_text):
    """Save the transformed text to a new file."""
    # Create output filename
    base_name = os.path.splitext(original_file_path)[0]
    extension = os.path.splitext(original_file_path)[1]
    output_file = f"{base_name}_happy{extension}"
    
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(transformed_text)
        print(f"Transformed text saved to: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error saving file: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Transform sad text to happy text using OpenAI API")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("--model", default="gpt-3.5-turbo", help="OpenAI model to use (default: gpt-3.5-turbo)")
    parser.add_argument("--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    # Hardcoded API key - replace with your actual key
    api_key = "MY_KEY_HERE"    
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    print(f"Reading file: {args.input_file}")
    original_text = read_text_file(args.input_file)
    
    print("Original text:")
    print("-" * 50)
    print(original_text)
    print("-" * 50)
    
    print("\nTransforming text with OpenAI...")
    transformed_text = transform_text_mood(client, original_text)
    
    print("\nTransformed text:")
    print("-" * 50)
    print(transformed_text)
    print("-" * 50)
    
    # Save transformed text
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as file:
            file.write(transformed_text)
        print(f"\nTransformed text saved to: {args.output}")
    else:
        save_transformed_text(args.input_file, transformed_text)

if __name__ == "__main__":
    main()

import csv
import json
import os
import argparse
import logging
from typing import List, Dict
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def read_csv_file(file_path: str) -> List[Dict[str, str]]:
    try:
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            data = list(reader)
            logging.debug(f"Read {len(data)} rows from {file_path}")
            if data:
                logging.debug(f"Sample row: {data[0]}")
            return data
    except Exception as e:
        logging.error(f"Error reading CSV file {file_path}: {str(e)}")
        return []

def convert_to_training_data(conversations: List[Dict[str, str]], use_history: bool) -> List[Dict[str, any]]:
    training_data = []
    history = []
    instruction = ""


    for utterance in conversations:
        logging.debug(f"Processing turn: {utterance}")
        
        if 'Turn' not in utterance or 'Role' not in utterance or 'Content' not in utterance:
                logging.warning(f"Missing 'Turn', 'Role', or 'Content' in turn: {utterance}")
                continue
        

        role = utterance['Role'].strip().lower()
        content = utterance['Content'].strip()
        turn_number = int(utterance['Turn'])

        if use_history:
            print("trying to use history")
        else:
            # Skip turn 0
            if turn_number == 0:
                continue

            if role == 'user':
                instruction = content
                training_example = {
                    "instruction": instruction,
                    "input": "",
                    "output": "",
                    "history":[]
                } 
                training_data.append(training_example)
            elif role == 'assistant':
                response = content
                training_data[-1]["output"] = response
            else:
                logging.warning(f"Unknown role: {role}")

    logging.debug(f"Converted {len(training_data)} training examples")
    return training_data

def process_directory(directory: str, use_history: bool) -> List[Dict[str, any]]:
    all_training_data = []

    for filename in os.listdir(directory):
        if filename.endswith('.csv'):
            file_path = os.path.join(directory, filename)
            logging.info(f"Processing file: {file_path}")
            conversations = read_csv_file(file_path)
            training_data = convert_to_training_data(conversations, use_history)
            all_training_data.extend(training_data)

    logging.info(f"Total training examples: {len(all_training_data)}")
    return all_training_data

def process_file(file_path: str, use_history: bool) -> List[Dict[str, any]]:
    training_data = []

    logging.info(f"Processing file: {file_path}")
    conversation = read_csv_file(file_path)
    training_data = convert_to_training_data(conversation, use_history)

    logging.info(f"Single run of training examples completed")
    return training_data

def save_to_json(data: List[Dict[str, any]], output_file: str):
    try:
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        logging.info(f"Data successfully saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving JSON file {output_file}: {str(e)}")

def get_timestamped_filename(base_filename: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = os.path.splitext(base_filename)
    return f"{name}_{timestamp}{ext}"

def main():
    parser = argparse.ArgumentParser(description="Convert CSV files to JSON format for LLM training.")
    parser.add_argument("--mode", choices=["file", "dir"], default="dir", 
                        help="Run mode: 'file' for single file, 'dir' for processing all files in a directory")
    parser.add_argument("-i", "--input", default="./output", help="Input single file or directory containing multiple files")
    parser.add_argument("-o", "--output_file", default="training_data.json", help="Base name for output JSON file")
    parser.add_argument("--history", action="store_true", help="Include conversation history in the output")
    parser.set_defaults(history=False)

    args = parser.parse_args()

    logging.info(f"Starting processing in {args.mode} mode")
    logging.info(f"With input: {args.input}")
    logging.info(f"History {'enabled' if args.history else 'disabled'}")

    timestamped_output_file = get_timestamped_filename(args.output_file)

    if args.mode == "file":
        training_data = process_file(args.input, use_history=args.history)
    elif args.mode == "dir":
        training_data = process_directory(args.input, use_history=args.history)
    
    if not training_data:
        logging.warning("No training data generated. Check your input files and directory.")
    
    save_to_json(training_data, timestamped_output_file)
    print(f"Training data {'with' if args.history else 'without'} history saved to {timestamped_output_file}")

if __name__ == "__main__":
    main()
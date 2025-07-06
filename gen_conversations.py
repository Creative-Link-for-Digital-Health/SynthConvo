import argparse
import os
import pandas as pd
from conversation_two_personas import generate_conversation

def process_file(file_path, num_turns, num_times):

    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            vignette = file.read()

        for _ in range(num_times):
            generate_conversation(vignette, num_turns)

    except UnicodeDecodeError:
        print(f"Error: Unable to read {file_path}. It may not be a text file.")
        return None
    except IOError as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def process_csv(csv_path, num_turns, num_times):

    try:
        df = pd.read_csv(csv_path)
        if 'content' not in df.columns:
            print("Error: CSV must contain a 'content' column")
            return

        for index, row in df.iterrows():
            vignette = row['content']
        
            for _ in range(num_times):
                generate_conversation(vignette, num_turns)    

    except pd.errors.EmptyDataError:
        print(f"The CSV file {csv_path} is empty.")
    except pd.errors.ParserError:
        print(f"Error parsing the CSV file {csv_path}. Please check the file format.")

def main():
    parser = argparse.ArgumentParser(
        description="Batch Conversation Generator: Process single files or multiple files listed in a CSV.",
        epilog="Example usage:\n"
               "  Single file: python batch_conversations.py --mode file --path /path/to/your/file.py --turns 10\n"
               "  CSV file: python batch_conversations.py --mode csv --path /path/to/your/csv_file.csv --turns 10",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mode", choices=["file", "csv"], required=True, 
                        help="Run mode: 'file' for single file, 'csv' for processing files listed in a CSV")
    parser.add_argument("--path", required=True, 
                        help="Path to the file or CSV. For 'file' mode, specify the file to process. "
                             "For 'csv' mode, specify the CSV file containing a list of files to process.")
    parser.add_argument("--turns", type=int, default=5, 
                        help="Number of turns that the conversation generator uses for each dialog conversation it generates. The default is 5.")
    parser.add_argument("--times", type=int, default=1, 
                        help="Number of times a vignette is used to generate a dialog")
    

    args = parser.parse_args()
    
    if args.mode == "file":
        if os.path.exists(args.path):
            process_file(args.path, args.turns, args.times)
        else:
            print(f"File not found: {args.path}")
    elif args.mode == "csv":
        if os.path.exists(args.path):
            process_csv(args.path, args.turns, args.times)
        else:
            print(f"CSV file not found: {args.path}")

if __name__ == "__main__":
    main()
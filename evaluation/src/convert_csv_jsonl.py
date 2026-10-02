try:
    import pandas as pd
    pandas_available = True
except ImportError:
    pandas_available = False
import json
import csv
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert CSV to JSONL format.')
    parser.add_argument('output_jsonl', type=str, help='Path to the output JSONL file.')
    parser.add_argument('input_csv', type=str, nargs='+', help='Paths to the input CSV files.')
    args = parser.parse_args()

    if pandas_available:
        df = pd.read_csv(args.input_csv)
        df.to_json(args.output_jsonl, orient='records', lines=True)
    else:
        with open(args.input_csv, mode='r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            with open(args.output_jsonl, mode='w', encoding='utf-8') as jsonl_file:
                for row in reader:
                    jsonl_file.write(json.dumps(row) + '\n')
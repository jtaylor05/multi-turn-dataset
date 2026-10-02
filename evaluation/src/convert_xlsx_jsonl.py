import pandas as pd
import argparse
import os

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert XLSX to JSONL format.')
    parser.add_argument('output_dir', type=str, help='Path to the output directory.')
    parser.add_argument('input_xlsx', type=str, nargs='+', help='Paths to the input XLSX files.')
    args = parser.parse_args()

    for xlsx_file in args.input_xlsx:
        df = pd.ExcelFile(xlsx_file)
        for sheet_name in df.sheet_names:
            sheet_df = pd.read_excel(xlsx_file, sheet_name=sheet_name)
            sheet_df.to_json(os.path.join(args.output_dir, f"{sheet_name}.jsonl"), orient='records', index=False, lines=True)
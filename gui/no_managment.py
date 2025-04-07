import pandas as pd
from datetime import datetime
import os

def process_file(file_path, delimiter):
    """Process a file and return a DataFrame with the first column."""
    try:
        df = pd.read_csv(file_path, header=None, sep=delimiter, dtype=str)  # Read the entire file with no header
        if df.shape[1] != 2:  # Check if the DataFrame has exactly 2 columns
            print(f"Skipping {file_path}: Expected 2 columns, found {df.shape[1]}.")
            return None
        df.columns = ['CUENTA', 'SECOND_COLUMN']  # Rename the columns
        return df[['CUENTA']]  # Return only the first column
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def transform_no_management(input_folder, output_folder):
    """Transform files in the input folder and save combined results."""
    try:
        # List all CSV and TXT files in the input folder
        files = [f for f in os.listdir(input_folder) if f.endswith('.csv') or f.endswith('.txt')]
        if not files:
            raise FileNotFoundError("No CSV or TXT files found in the input folder.")
        
        df_list = []
        for file_name in files:
            file_path = os.path.join(input_folder, file_name)
            # Print the processing message with the specified format
            print(f"No Management Processing: {file_name} - Registers: ", end='')  # Changed line
            
            if file_name.endswith('.csv'):
                df = process_file(file_path, delimiter=';')  # Process CSV with ';' delimiter
            elif file_name.endswith('.txt'):
                # Check the delimiter based on the file extension
                if '|' in open(file_path).readline():
                    df = process_file(file_path, delimiter='|')  # Process TXT with '|' delimiter
                else:
                    df = process_file(file_path, delimiter=' ')  # Process space-delimited TXT
            
            if df is not None:
                df_list.append(df)
                print(len(df))  # Print the number of records processed for the current file
            
        if not df_list:
            raise ValueError("No DataFrames were processed. Ensure files contain data.")
        
        # Combine all DataFrames and drop duplicates
        combined_df = pd.concat(df_list, ignore_index=True).drop_duplicates()
        combined_df['CUENTA'] = combined_df['CUENTA'].str.replace('.', '', regex=False)
        combined_df = combined_df[combined_df['CUENTA'].str.isnumeric()]

        if not combined_df.empty:
            combined_df['FECHA'] = datetime.now().strftime('%Y-%m-%d')  # Add current date
            output_file = f'No Gestion {datetime.now().strftime("%Y-%m-%d_%H-%M")}.csv'
            output_path = os.path.join(output_folder, output_file)
            combined_df.to_csv(output_path, index=False, header=True, sep=';')
            print(f"\nData saved to {output_path} with {len(combined_df)} records.")
        else:
            print("\nThe combined DataFrame is empty. No action taken.")
    except Exception as e:
        print(f"An error occurred: {e}")
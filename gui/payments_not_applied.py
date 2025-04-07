import pandas as pd
from openpyxl import load_workbook
from datetime import datetime
import os

def clean_and_process(df, archivo_label):
    """Cleans the DataFrame and adds the ARCHIVO column."""
    
    if 'REFERENCIA_DIVIDIDA' in df.columns:
        df = df.rename(columns={'REFERENCIA_DIVIDIDA': 'CUENTA'})
    if 'REFERENCIA DIVIDIDA' in df.columns:
        df = df.rename(columns={'REFERENCIA DIVIDIDA': 'CUENTA'})
    if 'CUSTCODE' in df.columns:
        df = df.rename(columns={'CUSTCODE': 'CUENTA'})
    if 'CUENTA' in df.columns:
        df['CUENTA'] = df['CUENTA'].astype(str).str.replace('.', '', regex=False).str[-9:]
        df = df[df['CUENTA'].str.isnumeric()]
        df['ARCHIVO'] = archivo_label
    else:
        print(f"No CUENTA column found in {archivo_label} sheet.")
    return df[['CUENTA', 'ARCHIVO']] if not df.empty else None

def process_file(file_path):
    """Processes the Excel file and returns the cleaned DataFrame."""
    df = None
    try:
        xls = pd.ExcelFile(file_path)
        sheet_mapping = {
            'CONSO_Pagos MOVIL': 'Consolidado',
            'CONSO_Pagos_MOVIL': 'Consolidado',
            'Pagos_Sin_Aplicar_Fijo': 'Fijo',
            'Pagos_Sin_Aplicar Fijo': 'Fijo',
            'pagosmovil2': 'Movil',
            'pagos MOVIL 2': 'Movil'
        }
        for sheet_name, archivo_label in sheet_mapping.items():
            if sheet_name in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name, dtype=str)
                return clean_and_process(df, archivo_label)
        print(f"No relevant sheets found in {file_path}.")
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return None

def Transform_Payments_without_Applied(input_folder, output_folder):
    """Transform payments without applied status from Excel files."""
    try:
        excel_files = [f for f in os.listdir(input_folder) if f.endswith('.xlsx')]
        if not excel_files:
            raise FileNotFoundError("No Excel files found in the input folder.")
        
        df_list = []
        for file_name in excel_files:
            file_path = os.path.join(input_folder, file_name)
            # Print the processing message with the specified format
            print(f"Payments not Applied Processing: {file_name} - Registers: ", end='')  # Changed line
            
            df = process_file(file_path)
            if df is not None:
                df_list.append(df)
                print(len(df))  # Print the number of records processed for the current file
        
        if not df_list:
            raise ValueError("No DataFrames were processed. Ensure Excel files contain the specified sheets.")
        
        combined_df = pd.concat(df_list, ignore_index=True).drop_duplicates()
        if len(combined_df) > 5:
            combined_df['FECHA'] = datetime.now().strftime('%Y-%m-%d')
            output_file = f'Pagos sin Aplicar {datetime.now().strftime("%Y-%m-%d_%H-%M")}.csv'
            output_path = os.path.join(output_folder, output_file)
            combined_df[['CUENTA', 'FECHA']].to_csv(output_path, index=False, header=True, sep=';')
            print(f"\nData PSA saved to {output_path} with {len(combined_df)} records.")
        else:
            print("\nThe combined DataFrame does not have more than 5 records. No action taken.")
    except Exception as e:
        print(f"An error occurred: {e}")
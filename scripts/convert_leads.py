import pandas as pd
import re
import os
import sys
from datetime import datetime

def clean_phone_number(phone):
    """Clean phone numbers by removing non-digit characters."""
    if pd.isna(phone) or phone == 'NA':
        return ''
    
    # Convert to string and remove the decimal point
    phone_str = str(phone).replace('.0', '')
    # Remove any non-digit characters
    cleaned = re.sub(r'[^0-9]', '', phone_str)
    return cleaned

def format_name(name):
    """Convert a name to proper case format."""
    if pd.isna(name) or not isinstance(name, str):
        return name
    
    # Split by spaces and handle each part
    parts = name.strip().split()
    formatted_parts = []
    
    for part in parts:
        # Handle hyphenated names
        if '-' in part:
            hyphen_parts = part.split('-')
            formatted_part = '-'.join(p.capitalize() for p in hyphen_parts)
        else:
            formatted_part = part.capitalize()
        
        formatted_parts.append(formatted_part)
    
    return ' '.join(formatted_parts)

def format_email(email):
    """Format email addresses to be lowercase."""
    if pd.isna(email) or not isinstance(email, str):
        return email
    
    return email.lower()

def convert_money_to_numeric(value):
    """Convert money values from string format to numeric."""
    if pd.isna(value):
        return 1300000  # Default value
    
    # Check if it's a money value string
    if isinstance(value, str) and "R$" in value:
        # Remove R$, commas, and spaces
        value_str = str(value).replace('R$', '').replace(',', '').replace('.00', '').replace(' ', '')
        # Convert to integer
        try:
            return int(value_str)
        except:
            return 1300000  # Default value if conversion fails
    else:
        # Not a money format, use default
        return value

def format_description(desc):
    """Format description field by replacing commas with semicolons."""
    if pd.isna(desc) or not isinstance(desc, str):
        return desc
        
    return desc.replace(',', ';')

def main():
    print(f"Starting leads conversion process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Define input and output paths
    input_dir = os.path.join(os.getcwd(), 'A converter')
    input_file = os.path.join(input_dir, 'leads-semformatado.csv')
    output_file = os.path.join(os.getcwd(), 'Novos_Leads_Sales.csv')
    
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist.")
        sys.exit(1)
    
    # Read the input CSV file
    try:
        df = pd.read_csv(input_file)
        print(f"Successfully read file. Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    print("\nApplying transformations...")
    
    # Format names and emails
    if 'Cliente' in df.columns:
        df['Cliente'] = df['Cliente'].apply(format_name)
    if 'E-mail' in df.columns:
        df['E-mail'] = df['E-mail'].apply(format_email)
    
    # Clean phone numbers
    if 'Celular' in df.columns:
        df['Celular'] = df['Celular'].apply(clean_phone_number)
    if 'Tel. Fixo' in df.columns:
        df['Tel. Fixo'] = df['Tel. Fixo'].apply(clean_phone_number)
    
    # Format description
    if 'Descrição' in df.columns:
        df['Descrição'] = df['Descrição'].apply(format_description)
    
    # Convert money values
    if 'Volume Aproximado' in df.columns:
        df['Volume Aproximado'] = df['Volume Aproximado'].apply(convert_money_to_numeric)
    
    # Rename columns according to the transformation rules in README
    column_mapping = {
        'Cliente': 'LastName',
        'Volume Aproximado': 'Patrimônio Financeiro',
        'Proprietario': 'OwnerId',
        'Milhao': 'Lead tem mais de R$1M?',
        'Estado': 'Estado/Província',
        'Tipo': 'Tipo',  # This stays the same
        'Descrição': 'Descrição do Lead',
        'Tel. Fixo': 'Telefone Adicional',
        'Celular': 'Phone',
        'E-mail': 'Email'
    }
    
    # Apply the column mapping
    df = df.rename(columns=column_mapping)
    
    # Make sure all required columns exist
    required_columns = ['LastName', 'Telefone Adicional', 'Phone', 'Email', 'Descrição do Lead', 
                        'Patrimônio Financeiro', 'Tipo', 'Estado/Província', 'OwnerId', 'Lead tem mais de R$1M?']
    
    for col in required_columns:
        if col not in df.columns:
            print(f"Warning: Adding missing column {col}")
            df[col] = ""
    
    # Ensure the correct column order
    df = df[required_columns]
    
    # Save the processed data to the output file
    try:
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nConversion completed successfully!")
        print(f"Processed data saved to: {output_file}")
        print(f"Final dataframe shape: {df.shape}")
        print(f"Final columns: {df.columns.tolist()}")
    except Exception as e:
        print(f"Error saving file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

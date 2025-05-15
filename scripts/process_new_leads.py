import pandas as pd
import re
import os
import sys

# Print the current working directory
print(f"Current working directory: {os.getcwd()}")
print("Processing leads from 'A converter' directory...")

# Function to clean phone numbers
def clean_phone_number(phone):
    if pd.isna(phone) or phone == 'NA':
        return ''
    # Extract only digits from the phone number
    cleaned = re.sub(r'[^0-9]', '', str(phone))
    return cleaned

# Function to convert money values to numeric values
def convert_money_to_numeric(value):
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
        return 1300000

# Read the source CSV file
try:
    input_dir = os.path.join(os.getcwd(), 'A converter')
    input_file = os.path.join(input_dir, 'leads-formatado.csv')
    
    # If the formatted file doesn't exist, try to use the unformatted file directly
    if not os.path.exists(input_file):
        input_file = os.path.join(input_dir, 'leads-semformatado.csv')
        print(f"Formatted file not found, using original file: {input_file}")
    
    df = pd.read_csv(input_file)
    print(f"Successfully read file: {input_file}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)

# Rename columns to match the target format based on README specifications
print("Renaming columns...")
column_mapping = {
    'Cliente': 'Last Name',
    'Tel. Fixo': 'Telefone Adicional',
    'Celular': 'Phone',
    'E-mail': 'Email',
    # Removed Description field as it doesn't exist in Salesforce Lead object
    'Volume Aproximado': 'Patrimônio Financeiro',
    'Tipo': 'Tipo',
    'Estado': 'Estado/Província',
    'Proprietario': 'OwnerId',
    'Milhao': 'Lead tem mais de R$1M?'
}
df = df.rename(columns=column_mapping)

# Clean phone numbers
print("Cleaning phone numbers...")
if 'Phone' in df.columns:
    df['Phone'] = df['Phone'].apply(clean_phone_number)
if 'Telefone Adicional' in df.columns:
    df['Telefone Adicional'] = df['Telefone Adicional'].apply(clean_phone_number)

# Note: Description field is not available in Lead object, so we will skip processing it
print("Note: Description field is not being used (not available in Lead object)")

# Convert money values to numeric if needed
print("Converting money values...")
if 'Volume Aproximado' in df.columns:
    df['Patrimônio Financeiro'] = df['Volume Aproximado'].apply(convert_money_to_numeric)

# Ensure Milhao/Lead tem mais de R$1M? has the correct values
if 'Milhao' in df.columns:
    df['Lead tem mais de R$1M?'] = df['Milhao']
elif 'Lead tem mais de R$1M?' not in df.columns:
    df['Lead tem mais de R$1M?'] = 1

# Make sure we have all required columns
required_columns = ['Last Name', 'Telefone Adicional', 'Phone', 'Email', 
                    'Patrimônio Financeiro', 'Tipo', 'Estado/Província', 'OwnerId', 'Lead tem mais de R$1M?']

for col in required_columns:
    if col not in df.columns:
        print(f"Warning: Adding missing column {col}")
        df[col] = ""

# Save the result to the target file format
print("Saving processed file...")
# Remove original columns that have been transformed
for col in ['Volume Aproximado', 'Milhao', 'Cliente', 'Tel. Fixo', 'Celular', 'E-mail', 'Estado']:
    if col in df.columns:
        df = df.drop(columns=[col])

# Ensure no Description-related fields are passed to Salesforce
for col in ['Descrição', 'Descrição do Lead', 'Description']:
    if col in df.columns:
        df = df.drop(columns=[col])

# Reorder columns to match the target format
column_order = ['Last Name', 'Telefone Adicional', 'Phone', 'Email',
                'Patrimônio Financeiro', 'Tipo', 'Estado/Província', 'OwnerId', 'Lead tem mais de R$1M?']

# Make sure all columns exist before reordering
for col in column_order:
    if col not in df.columns:
        df[col] = ""

df = df[column_order]

output_file = os.path.join(os.getcwd(), 'Novos_Leads_Sales.csv')
df.to_csv(output_file, index=False, encoding='utf-8')

print(f"File has been processed successfully! Output saved to '{output_file}'")
print(f"Final dataframe shape: {df.shape}")
print(f"Final columns: {df.columns.tolist()}")

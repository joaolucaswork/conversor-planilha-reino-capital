import pandas as pd
import sys
import os
import re

print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")

def format_name(name):
    """Convert an uppercase name to proper case format."""
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

def clean_phone_number(phone):
    """Clean phone numbers by removing non-digit characters and .0 suffix."""
    if pd.isna(phone):
        return ''
    
    # Convert to string and remove the decimal point
    phone_str = str(phone).replace('.0', '')
    # Remove any non-digit characters
    cleaned = re.sub(r'[^0-9]', '', phone_str)
    return cleaned

def format_email(email):
    """Format email addresses to be lowercase."""
    if pd.isna(email) or not isinstance(email, str):
        return email
    
    return email.lower()

# Read the input file from 'A converter' directory
print("Reading CSV file...")
input_dir = os.path.join(os.getcwd(), 'A converter')
file_path = os.path.join(input_dir, 'leads-semformatado.csv')
print(f"File path: {file_path}")
print(f"File exists: {os.path.exists(file_path)}")

try:
    df = pd.read_csv(file_path)
    print(f"Successfully read file. Shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
except Exception as e:
    print(f"Error reading file: {e}")
    sys.exit(1)

# Display a few rows before formatting
print("\nBefore formatting:")
print(df[['Cliente', 'E-mail']].head(3))

# Apply formatting
print("\nApplying formatting to Cliente and E-mail fields...")
df['Cliente'] = df['Cliente'].apply(format_name)
df['E-mail'] = df['E-mail'].apply(format_email)

# Clean phone numbers
print("\nCleaning phone numbers...")
df['Celular'] = df['Celular'].apply(clean_phone_number)
df['Tel. Fixo'] = df['Tel. Fixo'].apply(clean_phone_number)

# Display after formatting
print("\nAfter formatting:")
print(df[['Cliente', 'E-mail', 'Celular', 'Tel. Fixo']].head(3))

# Save the changes
print("\nSaving changes...")
try:
    output_path = os.path.join(input_dir, 'leads-formatado.csv')
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"File {output_path} has been created with properly formatted fields.")
except Exception as e:
    print(f"Error saving file: {e}")
    sys.exit(1)

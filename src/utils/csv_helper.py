import pandas as pd
import os
import logging

def fix_salesforce_lead_csv(csv_file_path):
    """Corrige o arquivo CSV para garantir que todos os leads tenham Company preenchido"""
    try:
        df = pd.read_csv(csv_file_path)
        if "Company" in df.columns:
            df["Company"] = df["Company"].fillna("Empresa Desconhecida")
            df.loc[df["Company"] == "", "Company"] = "Empresa Desconhecida"
        df.to_csv(csv_file_path, index=False)
        return csv_file_path
    except Exception as e:
        print(f"Erro ao corrigir o arquivo CSV: {str(e)}")
        return None

"""
Módulo para corrigir o arquivo CSV antes de enviar para o Salesforce
"""
import pandas as pd
import os
import logging

logger = logging.getLogger('salesforce_csv_helper')

def fix_salesforce_lead_csv(csv_file_path):
    """
    Corrige o arquivo CSV para garantir que todos os leads tenham os campos obrigatórios preenchidos
    antes de enviar para o Salesforce.
    
    Args:
        csv_file_path (str): Caminho para o arquivo CSV a ser corrigido
        
    Returns:
        str: Caminho para o arquivo CSV corrigido ou None em caso de erro
    """
    if not os.path.exists(csv_file_path):
        logger.error(f"Arquivo CSV não encontrado: {csv_file_path}")
        return None
        
    try:
        # Ler o arquivo CSV
        df = pd.read_csv(csv_file_path)
        
        # Verificar se as colunas obrigatórias existem
        required_columns = ["LastName", "Company"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""  # Criar coluna vazia se não existir
                
        # Preencher campos vazios ou NaN com valores padrão
        if "LastName" in df.columns:
            df["LastName"] = df["LastName"].fillna("Lead Sem Nome")
            # Para linhas onde está vazio (string vazia), use "Lead Sem Nome"
            df.loc[df["LastName"] == "", "LastName"] = "Lead Sem Nome"
            
        if "Company" in df.columns:
            df["Company"] = df["Company"].fillna("Empresa Desconhecida")
            # Para linhas onde está vazio (string vazia), use "Empresa Desconhecida"
            df.loc[df["Company"] == "", "Company"] = "Empresa Desconhecida"
        
        # Verificar se há apenas um nome completo em LastName e dividir em FirstName e LastName se necessário
        if "FirstName" not in df.columns:
            df["FirstName"] = ""
            
        # Para cada linha, verificar se LastName contém múltiplas palavras (nome completo)
        for idx, row in df.iterrows():
            last_name = str(row["LastName"]).strip()
            if " " in last_name and row["FirstName"] == "":
                # Dividir o LastName em FirstName (primeira palavra) e LastName (resto)
                parts = last_name.split(" ", 1)
                df.at[idx, "FirstName"] = parts[0]
                df.at[idx, "LastName"] = parts[1]
        
        # Salvar o arquivo corrigido no mesmo local
        df.to_csv(csv_file_path, index=False)
        logger.info(f"Arquivo CSV corrigido e salvo: {csv_file_path}")
        
        return csv_file_path
    except Exception as e:
        logger.error(f"Erro ao corrigir o arquivo CSV: {str(e)}")
        return None

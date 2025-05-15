"""
Módulo para interação com a API do Salesforce.
Responsável por criar, atualizar e consultar leads no Salesforce.
"""

import os
import json
import requests
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
from .salesforce_auth import get_salesforce_access_token
from ..utils.salesforce_logger import get_salesforce_logger
import sys
import re

# Configuração do logger
logger = get_salesforce_logger('salesforce_api')

def clean_phone_number(phone):
    """Limpa números de telefone removendo caracteres não numéricos."""
    if pd.isna(phone) or phone == 'NA':
        return ''
    
    # Converte para string e remove o ponto decimal
    phone_str = str(phone).replace('.0', '')
    # Remove caracteres não numéricos
    cleaned = re.sub(r'[^0-9]', '', phone_str)
    return cleaned

def format_name(name):
    """Converte um nome para o formato adequado (title case)."""
    if pd.isna(name) or not isinstance(name, str):
        return name
    
    # Divide por espaços e trata cada parte
    parts = name.strip().split()
    formatted_parts = []
    
    for part in parts:
        # Trata nomes com hífen
        if '-' in part:
            hyphen_parts = part.split('-')
            formatted_part = '-'.join(p.capitalize() for p in hyphen_parts)
        else:
            formatted_part = part.capitalize()
        
        formatted_parts.append(formatted_part)
    
    return ' '.join(formatted_parts)

def format_email(email):
    """Formata endereços de email para lowercase."""
    if pd.isna(email) or not isinstance(email, str):
        return email
    
    return email.lower()

def convert_money_to_numeric(value):
    """Converte valores monetários de formato string para numérico."""
    if pd.isna(value):
        return 1300000  # Valor padrão
    
    # Verifica se é uma string de valor monetário
    if isinstance(value, str) and "R$" in value:
        # Remove R$, vírgulas e espaços
        value_str = str(value).replace('R$', '').replace(',', '').replace('.00', '').replace(' ', '')
        # Converte para inteiro
        try:
            return int(value_str)
        except:
            return 1300000  # Valor padrão se a conversão falhar
    else:
        # Não está no formato monetário, usar o padrão
        return value

def normalize_line_endings(text):
    """
    Normaliza os finais de linha para o formato LF (Unix/Linux).
    Importante para compatibilidade com a Bulk API do Salesforce.
    """
    if not isinstance(text, str):
        return text
    
    # Primeiro convertemos todos os finais de linha para o formato UNIX (\n)
    return text.replace('\r\n', '\n').replace('\r', '\n')

def format_description(desc):
    """Formata o campo de descrição substituindo vírgulas por ponto e vírgula.
    Nota: Atualmente não utilizado já que o campo Description não está disponível no objeto Lead.
    """
    if pd.isna(desc) or not isinstance(desc, str):
        return desc
        
    return desc.replace(',', ';')

def process_csv_file():
    """
    Processa o arquivo CSV de leads para formatação adequada ao Salesforce.
    
    Returns:
        pandas.DataFrame: DataFrame com dados formatados ou None em caso de erro.
    """
    logger.info("Iniciando processamento do arquivo CSV")
    
    try:
        # Define caminhos de entrada e saída
        input_dir = os.path.join(os.getcwd(), 'A converter')
        input_file = os.path.join(input_dir, 'leads-semformatado.csv')
        output_file = os.path.join(os.getcwd(), 'Novos_Leads_Sales.csv')
        
        logger.debug(f"Arquivo de entrada: {input_file}")
        logger.debug(f"Arquivo de saída: {output_file}")
        
        # Verifica se o arquivo de entrada existe
        if not os.path.exists(input_file):
            logger.error(f"Erro: Arquivo de entrada {input_file} não existe.")
            return None
        
        # Lê o arquivo CSV de entrada
        df = pd.read_csv(input_file)
        logger.info(f"Arquivo lido com sucesso. Shape: {df.shape}")
        logger.debug(f"Colunas: {df.columns.tolist()}")
        
        # Aplica as transformações
        logger.info("Aplicando transformações aos dados")
        
        # Formata nomes e emails
        if 'Cliente' in df.columns:
            df['Cliente'] = df['Cliente'].apply(format_name)
        if 'E-mail' in df.columns:
            df['E-mail'] = df['E-mail'].apply(format_email)
        
        # Limpa números de telefone
        if 'Celular' in df.columns:
            df['Celular'] = df['Celular'].apply(clean_phone_number)
        if 'Tel. Fixo' in df.columns:
            df['Tel. Fixo'] = df['Tel. Fixo'].apply(clean_phone_number)
        
        # Formata descrição
        if 'Descrição' in df.columns:
            df['Descrição'] = df['Descrição'].apply(format_description)
        
        # Converte valores monetários
        if 'Volume Aproximado' in df.columns:
            df['Volume Aproximado'] = df['Volume Aproximado'].apply(convert_money_to_numeric)
        
        # Renomeia colunas de acordo com as regras de transformação no README
        column_mapping = {
            'Cliente': 'LastName',
            'Volume Aproximado': 'Patrimônio Financeiro',
            'Proprietario': 'OwnerId',
            'Milhao': 'Lead tem mais de R$1M?',
            'Estado': 'Estado/Província',
            'Tipo': 'Tipo',  # Este permanece o mesmo
            'Descrição': 'Descrição do Lead',
            'Tel. Fixo': 'Telefone Adicional',
            'Celular': 'Phone',
            'E-mail': 'Email'
        }
        
        # Aplica o mapeamento de colunas
        df = df.rename(columns=column_mapping)
        
        # Garante que todas as colunas necessárias existam
        required_columns = ['LastName', 'Telefone Adicional', 'Phone', 'Email', 'Descrição do Lead', 
                          'Patrimônio Financeiro', 'Tipo', 'Estado/Província', 'OwnerId', 'Lead tem mais de R$1M?']
        
        for col in required_columns:
            if col not in df.columns:
                logger.warning(f"Adicionando coluna ausente: {col}")
                df[col] = ""
        
        # Garante a ordem correta das colunas
        df = df[required_columns]
        
        # Salva os dados processados no arquivo de saída
        df.to_csv(output_file, index=False, encoding='utf-8', lineterminator='\n')
        logger.info(f"Conversão concluída com sucesso!")
        logger.info(f"Dados processados salvos em: {output_file}")
        logger.debug(f"Shape final do dataframe: {df.shape}")
        
        return df
    
    except Exception as e:
        logger.exception(f"Erro no processamento do arquivo: {str(e)}")
        return None

def create_lead_in_salesforce(lead_data):
    """
    Cria um novo lead no Salesforce.
    
    Args:
        lead_data (dict): Dados do lead a ser criado.
        
    Returns:
        str: ID do lead criado ou None em caso de erro.
    """
    logger.info("=== INICIANDO CRIAÇÃO DE LEAD NO SALESFORCE ===")
    
    # Garantir que campos obrigatórios estejam presentes
    if 'LastName' not in lead_data or not lead_data['LastName']:
        lead_data['LastName'] = 'Lead Sem Nome'
        logger.warning("Campo LastName ausente ou vazio. Usando valor padrão: 'Lead Sem Nome'")
    
    if 'Company' not in lead_data or not lead_data['Company']:
        lead_data['Company'] = 'Empresa Desconhecida'
        logger.warning("Campo Company ausente ou vazio. Usando valor padrão: 'Empresa Desconhecida'")
    
    logger.debug(f"Dados do lead: {lead_data}")
    
    try:
        # Obtém o token de acesso
        logger.debug("Obtendo token de acesso do Salesforce")
        access_token = get_salesforce_access_token()
        
        if not access_token:
            logger.error("Token de acesso vazio ou não obtido")
            return None
        
        logger.debug("Token de acesso obtido com sucesso")
        
        # Configura a requisição
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Define a URL da API baseada no ambiente configurado
        api_version = os.getenv('SALESFORCE_API_VERSION', '63.0')
        instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
        
        if not instance_url:
            logger.error("URL da instância do Salesforce não configurada")
            return None
        
        # Certifica-se que a versão da API está no formato correto (sem 'v' adicional)
        api_version_clean = api_version.replace('v', '')
        
        url = f"{instance_url}/services/data/v{api_version_clean}/sobjects/Lead"
        
        # Registra os detalhes antes de enviar
        logger.debug(f"Criando lead no Salesforce via POST para {url}")
        logger.debug(f"Payload: {json.dumps(lead_data, indent=2)}")
        
        # Tenta fazer a requisição para criar o lead
        start_time = time.time()
        response = requests.post(url, headers=headers, json=lead_data)
        request_time = time.time() - start_time
        
        # Registra a resposta e o tempo de requisição
        logger.debug(f"Tempo de requisição: {request_time:.2f} segundos")
        logger.debug(f"Status code: {response.status_code}")
        
        if response.status_code == 201:  # 201 significa Created
            result = response.json()
            lead_id = result.get('id')
            logger.info(f"Lead criado com sucesso! ID: {lead_id}")
            return lead_id
        elif response.status_code == 404:
            # Tratamento especial para erro 404 (Not Found)
            logger.error(f"ERRO 404: Endpoint não encontrado no Salesforce")
            logger.error(f"URL utilizada: {url}")
            logger.error(f"API Version: {api_version}, Instance URL: {instance_url}")
            logger.error(f"Payload: {json.dumps(lead_data, indent=2, default=str)}")
            logger.error(f"Resposta detalhada: {response.text}")
            
            # Verifica configurações potencialmente incorretas
            logger.debug("Verificando possíveis causas de erro 404:")
            if 'sobjects' not in url:
                logger.error("URL pode estar incorreta. 'sobjects' não encontrado na URL.")
            if not api_version:
                logger.error("Versão da API não definida corretamente.")
            if not instance_url:
                logger.error("URL da instância não definida corretamente.")
            
            return None
        else:
            logger.error(f"Erro ao criar lead. Status: {response.status_code}")
            logger.error(f"Resposta de erro: {response.text}")
            
            # Mais detalhes para ajudar na depuração
            try:
                error_details = response.json()
                if isinstance(error_details, list) and len(error_details) > 0:
                    for error in error_details:
                        logger.error(f"Erro: {error.get('message', 'Sem mensagem')}. Código: {error.get('errorCode', 'Sem código')}")
            except:
                logger.debug("Não foi possível analisar detalhes adicionais da resposta de erro")
                
            return None
    
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 404:
                logger.error(f"ERRO 404: Endpoint não encontrado. Verifique a URL e a versão da API: {url}")
                logger.error(f"Detalhes do erro 404: {e.response.text if hasattr(e.response, 'text') else 'Sem detalhes disponíveis'}")
                # Informação adicional para auxiliar no diagnóstico
                logger.error(f"API Version: {api_version}, Instance URL: {instance_url}")
                logger.error(f"Lead data: {json.dumps(lead_data, indent=2, default=str)}")
            else:
                logger.error(f"Erro HTTP {e.response.status_code} ao criar lead: {e.response.text if hasattr(e.response, 'text') else str(e)}")
        else:
            logger.exception(f"Exceção de requisição ao criar lead: {str(e)}")
        return None
    except Exception as e:
        logger.exception(f"Exceção não esperada ao criar lead: {str(e)}")
        return None


def create_bulk_leads_in_salesforce(leads_data):
    """
    Cria múltiplos leads de uma só vez no Salesforce usando a Bulk API 2.0.
    
    Args:
        leads_data (list): Lista de dicionários contendo dados de leads a serem criados.
        
    Returns:
        dict: Resultados da operação em massa com IDs e status de cada registro.
    """
    logger.info(f"=== INICIANDO CRIAÇÃO EM MASSA DE {len(leads_data)} LEADS NO SALESFORCE USANDO BULK API 2.0 ===")
    
    # Verificação preliminar dos dados
    if not leads_data:
        logger.error("Nenhum dado de lead fornecido para processamento em massa")
        return None
        
    # Verificar se há leads com os campos obrigatórios (LastName e Company)
    valid_leads = []
    for i, lead in enumerate(leads_data):
        if not isinstance(lead, dict):
            logger.warning(f"Lead {i+1} não é um dicionário válido, ignorando")
            continue
            
        if not lead.get('LastName'):
            lead['LastName'] = 'Lead Sem Nome'
            logger.warning(f"Lead {i+1} sem LastName, usando valor padrão")
            
        if not lead.get('Company'):
            lead['Company'] = 'Empresa Desconhecida'
            logger.warning(f"Lead {i+1} sem Company, usando valor padrão")
            
        valid_leads.append(lead)
        
    if not valid_leads:
        logger.error("Nenhum lead válido encontrado após verificação inicial")
        return None
        
    leads_data = valid_leads
    logger.info(f"{len(leads_data)} leads válidos para processamento após verificação inicial")
    
    try:
        # Obtém o token de acesso
        logger.debug("Obtendo token de acesso do Salesforce")
        access_token = get_salesforce_access_token()
        
        if not access_token:
            logger.error("Token de acesso vazio ou não obtido")
            return None
        
        logger.debug("Token de acesso obtido com sucesso")
        
        # Configura a requisição
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        # Define a URL da API baseada no ambiente configurado
        api_version = os.getenv('SALESFORCE_API_VERSION', '63.0')
        instance_url = os.getenv('SALESFORCE_INSTANCE_URL')
        
        if not instance_url:
            logger.error("URL da instância do Salesforce não configurada")
            return None
        
        # Certifica-se que a versão da API está no formato correto (sem 'v' adicional)
        api_version_clean = api_version.replace('v', '')
        
        # Etapa 1: Criar um job usando a Bulk API 2.0
        create_job_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest"
        
        job_data = {
            "object": "Lead",
            "contentType": "CSV",
            "operation": "insert",
            "lineEnding": "LF"  # Explicitamente definindo final de linha como LF
        }
        
        logger.debug(f"Criando job da Bulk API em: {create_job_url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Dados do job: {job_data}")
        
        job_response = requests.post(create_job_url, headers=headers, json=job_data)
        
        if job_response.status_code != 200:
            logger.error(f"Erro ao criar job da Bulk API. Status: {job_response.status_code}")
            logger.error(f"Resposta: {job_response.text}")
            # Detalhamento adicional do erro
            try:
                error_json = job_response.json()
                if isinstance(error_json, list) and len(error_json) > 0:
                    for error in error_json:
                        logger.error(f"Código de erro: {error.get('errorCode')}, Mensagem: {error.get('message')}")
                elif isinstance(error_json, dict):
                    logger.error(f"Código de erro: {error_json.get('errorCode')}, Mensagem: {error_json.get('message')}")
            except Exception as e:
                logger.error(f"Não foi possível analisar detalhes do erro: {str(e)}")
            
            # Verifique os elementos específicos da requisição
            logger.debug(f"Headers enviados: {json.dumps(headers)}")
            logger.debug(f"Dados do job enviados: {json.dumps(job_data)}")
            logger.debug(f"URL completa: {create_job_url}")
            return None
        
        job_info = job_response.json()
        job_id = job_info.get('id')
        logger.info(f"Job da Bulk API criado com sucesso. ID: {job_id}")
        
        # Etapa 2: Fazer upload dos dados para o job
        upload_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}/batches"
        
        # Prepara os dados como CSV
        upload_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'text/csv',
            'Accept': 'application/json'
        }
        
        # Converte os dados para formato CSV
        df_leads = pd.DataFrame(leads_data)
        
        # Verificando e renomeando colunas para garantir compatibilidade com Salesforce
        rename_mapping = {}
        for col in df_leads.columns:
            # Remover espaços e caracteres especiais do nome da coluna
            new_col = col.strip().replace(' ', '_')
            if col != new_col:
                rename_mapping[col] = new_col
        
        if rename_mapping:
            df_leads = df_leads.rename(columns=rename_mapping)
            logger.debug(f"Colunas renomeadas: {rename_mapping}")
        
        # Garantir que todos os valores sejam strings para evitar problemas de formatação
        for col in df_leads.columns:
            df_leads[col] = df_leads[col].astype(str)
            # Substituir valores 'nan' por strings vazias
            df_leads[col] = df_leads[col].replace('nan', '')
        
        # Remover colunas vazias ou nulas
        df_leads = df_leads.dropna(axis=1, how='all')
        
        # Garantir que campos obrigatórios estejam presentes
        if 'LastName' not in df_leads.columns:
            logger.warning("Adicionando campo obrigatório 'LastName' aos dados")
            df_leads['LastName'] = 'Lead Sem Nome'
            
        if 'Company' not in df_leads.columns:
            logger.warning("Adicionando campo obrigatório 'Company' aos dados")
            df_leads['Company'] = 'Empresa Desconhecida'
            
        # Lista de colunas no CSV para debug
        logger.debug(f"Colunas no CSV: {df_leads.columns.tolist()}")

        # Verificar e limpar valores excessivamente longos para evitar erros
        for col in df_leads.columns:
            max_len = df_leads[col].astype(str).str.len().max()
            if max_len > 255:
                logger.warning(f"Campo {col} contém valores longos (max: {max_len}). Truncando para 255 caracteres.")
                df_leads[col] = df_leads[col].astype(str).str.slice(0, 255)

        # Verificar tamanho do DataFrame
        logger.debug(f"Tamanho do DataFrame: {df_leads.shape}")
        
        # Converter para CSV com encoding adequado e garantir que os finais de linha sejam LF
        csv_data = df_leads.to_csv(index=False, encoding='utf-8', lineterminator='\n')
        
        # Garantir que o final de linha está no formato LF (Unix-style)
        csv_data = csv_data.replace('\r\n', '\n')
        
        # Salvar temporariamente o CSV para verificação (apenas em ambiente de desenvolvimento)
        try:
            temp_csv_path = os.path.join(os.getcwd(), 'A converter', 'temp', f'bulk_api_data_{time.strftime("%Y%m%d_%H%M%S")}.csv')
            os.makedirs(os.path.dirname(temp_csv_path), exist_ok=True)
            with open(temp_csv_path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(csv_data)
            logger.debug(f"CSV salvo temporariamente em: {temp_csv_path}")
        except Exception as e:
            logger.warning(f"Não foi possível salvar CSV temporário: {str(e)}")
        
        # Registra os primeiros 500 caracteres do CSV para verificação
        logger.debug(f"Amostra do CSV (primeiros 500 caracteres): {csv_data[:500]}")
        logger.debug(f"Tamanho total do CSV: {len(csv_data)} bytes")
        
        # Verifica se o CSV contém caracteres CR (\r) o que indicaria finais de linha incorretos
        has_cr = '\r' in csv_data
        logger.debug(f"CSV contém caracteres CR (\\r)? {'Sim' if has_cr else 'Não'}")
        if has_cr:
            logger.warning("O CSV contém caracteres CR (\\r), isso pode causar problemas com a Bulk API do Salesforce")
            csv_data = normalize_line_endings(csv_data)
            logger.info("Finais de linha normalizados para formato LF")
        
        logger.debug(f"Enviando {len(leads_data)} registros para o job {job_id} em formato CSV")
        
        upload_response = requests.put(upload_url, headers=upload_headers, data=csv_data)
        
        if upload_response.status_code != 201:
            logger.error(f"Erro ao enviar dados para o job. Status: {upload_response.status_code}")
            logger.error(f"Resposta: {upload_response.text}")
            
            # Informações adicionais para depuração
            logger.debug(f"Headers do upload: {upload_headers}")
            logger.debug(f"Tamanho dos dados CSV: {len(csv_data)} bytes")
            logger.debug(f"Primeiras 500 caracteres dos dados: {csv_data[:500]}")
            
            # Tentar fechar o job com status de fracasso
            abort_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}"
            abort_data = {"state": "Aborted"}
            abort_response = requests.patch(abort_url, headers=headers, json=abort_data)
            logger.debug(f"Resposta ao abortar job: Status {abort_response.status_code}, {abort_response.text}")
            
            return None
        
        # Etapa 3: Finalizar o job para iniciar o processamento
        close_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}"
        close_data = {"state": "UploadComplete"}
        
        logger.debug(f"Finalizando job {job_id} para iniciar processamento")
        close_response = requests.patch(close_url, headers=headers, json=close_data)
        
        if close_response.status_code != 200:
            logger.error(f"Erro ao finalizar job. Status: {close_response.status_code}")
            logger.error(f"Resposta: {close_response.text}")
            return None
        
        # Etapa 4: Verificar o status do job até que termine
        max_attempts = 30  # Número máximo de tentativas (5 minutos com 10 segundos entre tentativas)
        attempts = 0
        finished = False
        
        logger.info(f"Job {job_id} iniciado. Monitorando progresso...")
        
        while attempts < max_attempts and not finished:
            attempts += 1
            time.sleep(10)  # Esperar 10 segundos entre verificações
            
            status_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}"
            status_response = requests.get(status_url, headers=headers)
            
            if status_response.status_code != 200:
                logger.warning(f"Erro ao verificar status do job. Tentativa {attempts} de {max_attempts}")
                continue
            
            status_info = status_response.json()
            job_state = status_info.get('state')
            
            logger.debug(f"Status do job: {job_state} (Tentativa {attempts}/{max_attempts})")
            
            if job_state in ['JobComplete', 'Failed', 'Aborted']:
                finished = True
                logger.info(f"Job finalizado com status: {job_state}")
                break
        
        if not finished:
            logger.error(f"Timeout aguardando conclusão do job após {max_attempts} tentativas")
            return None                # Etapa 5: Obter os resultados do job
        results_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}/successfulResults"
        failed_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}/failedResults"
        
        # Obter informações completas do job antes de obter resultados
        job_details_url = f"{instance_url}/services/data/v{api_version_clean}/jobs/ingest/{job_id}"
        details_response = requests.get(job_details_url, headers=headers)
        
        if details_response.status_code == 200:
            job_details = details_response.json()
            logger.info(f"Detalhes completos do job: {json.dumps(job_details, indent=2)}")
            
            # Extrair informações importantes para diagnóstico
            if 'errorMessage' in job_details and job_details['errorMessage']:
                error_message = job_details['errorMessage']
                logger.error(f"Mensagem de erro do job: {error_message}")
                
                # Verificar erros específicos
                if "LineEnding is invalid on user data" in error_message:
                    logger.error("Erro de final de linha detectado. Isso geralmente acontece quando os finais de linha no CSV não são compatíveis com a configuração do Salesforce.")
                    logger.error("Tentar novamente com a correção de final de linha implementada.")
            
            if 'state' in job_details:
                logger.info(f"Estado final do job: {job_details['state']}")
                
            if 'numberRecordsProcessed' in job_details:
                logger.info(f"Registros processados: {job_details['numberRecordsProcessed']}")
                
            if 'numberRecordsFailed' in job_details:
                logger.info(f"Registros com falha: {job_details['numberRecordsFailed']}")
                
            if 'contentType' in job_details:
                logger.debug(f"Tipo de conteúdo usado: {job_details['contentType']}")
        else:
            logger.error(f"Erro ao obter detalhes do job. Status: {details_response.status_code}, Resposta: {details_response.text}")
        
        # Obter resultados de sucesso
        success_response = requests.get(results_url, headers=headers)
        
        success_results = []
        failed_results = []
        
        if success_response.status_code == 200:
            # Parse CSV results
            success_data = success_response.text
            success_lines = success_data.strip().split('\n')
            
            # Pular o cabeçalho CSV
            if len(success_lines) > 1:
                for line in success_lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 2:
                        success_results.append({
                            'sf_id': parts[0].strip('"'),
                            'index': int(parts[1])
                        })
        
        # Obter resultados de falha
        failed_response = requests.get(failed_url, headers=headers)
        
        if failed_response.status_code == 200:
            # Parse CSV results
            failed_data = failed_response.text
            logger.debug(f"Dados de resultados falhos: {failed_data[:1000] if len(failed_data) > 1000 else failed_data}")
            
            failed_lines = failed_data.strip().split('\n')
            
            # Pular o cabeçalho CSV
            if len(failed_lines) > 1:
                logger.info(f"Cabeçalho dos resultados falhos: {failed_lines[0]}")
                for i, line in enumerate(failed_lines[1:]):
                    if i < 10:  # Limitamos a 10 registros para o log não ficar muito grande
                        parts = line.split(',')
                        logger.debug(f"Falha #{i+1}: {line}")
                        if len(parts) >= 3:
                            failed_results.append({
                                'index': int(parts[0]) if parts[0].isdigit() else 0,
                                'error': parts[1].strip('"'),
                                'error_fields': parts[2].strip('"') if len(parts) > 2 else ''
                            })
                        else:
                            logger.warning(f"Formato de linha falha inesperado: {line}")
                
                if len(failed_lines) > 11:
                    logger.info(f"... mais {len(failed_lines) - 11} linhas de falha não mostradas no log")
        else:
            logger.error(f"Erro ao obter resultados falhos. Status: {failed_response.status_code}, Resposta: {failed_response.text}")
        # Compila e retorna os resultados finais
        final_results = {
            'job_id': job_id,
            'state': job_state,
            'success_count': len(success_results),
            'failed_count': len(failed_results),
            'total_processed': status_info.get('numberRecordsProcessed', 0),
            'successful_records': success_results,
            'failed_records': failed_results
        }
        
        logger.info(f"Processamento em massa concluído: {final_results['success_count']} de {final_results['total_processed']} registros processados com sucesso")
        return final_results
    
    except Exception as e:
        logger.exception(f"Erro ao processar leads em massa: {str(e)}")
        return None


def create_leads_from_csv(csv_file_path, environment, owner_id=None):
    """
    Processa o arquivo CSV e cria leads no Salesforce usando a Bulk API 2.0 para maior eficiência.
    
    Args:
        csv_file_path (str): Caminho para o arquivo CSV a ser processado
        environment (str): Ambiente do Salesforce ('sandbox' ou 'production')
        owner_id (str, optional): ID do proprietário do lead no Salesforce.
            Se None, usa a atribuição automática do Salesforce.
    
    Returns:
        tuple: (success, results) onde success é um boolean e results são os resultados detalhados
    """
    logger.info(f"Iniciando processamento em massa de CSV: {csv_file_path}")
    logger.info(f"Ambiente: {environment}, Owner ID: {owner_id if owner_id else 'Atribuição automática'}")
    
    try:
        # Define variáveis de ambiente para a autenticação
        if environment.lower() == 'sandbox':
            os.environ['SALESFORCE_LOGIN_URL'] = os.getenv('SALESFORCE_SANDBOX_URL', 'https://test.salesforce.com')
            logger.info("Configurado para ambiente de SANDBOX")
        else:
            os.environ['SALESFORCE_LOGIN_URL'] = os.getenv('SALESFORCE_PRODUCTION_URL', 'https://login.salesforce.com')
            logger.info("Configurado para ambiente de PRODUÇÃO")
        
        # Verifica se o arquivo existe
        if not Path(csv_file_path).exists():
            logger.error(f"Arquivo não encontrado: {csv_file_path}")
            return False, f"Arquivo não encontrado: {csv_file_path}"
        
        # Lê o arquivo CSV
        logger.info(f"Lendo arquivo CSV: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        logger.info(f"Arquivo CSV lido com sucesso. {len(df)} registros encontrados.")
        
        # Ajusta nomes de colunas - remove espaços extras
        df.columns = [col.strip() for col in df.columns]
        
        # Limpa dados e formata campos
        logger.info("Aplicando formatação e limpeza aos dados")
        
        if 'Phone' in df.columns:
            df['Phone'] = df['Phone'].apply(clean_phone_number)
            logger.debug("Números de telefone limpos")
        
        if 'FirstName' in df.columns:
            df['FirstName'] = df['FirstName'].apply(format_name)
            logger.debug("Primeiros nomes formatados")
            
        if 'LastName' in df.columns:
            df['LastName'] = df['LastName'].apply(format_name)
            logger.debug("Sobrenomes formatados")
            
        if 'Email' in df.columns:
            df['Email'] = df['Email'].apply(format_email)
            logger.debug("Emails formatados")
            
        # Total de registros para processar
        total_count = len(df)
        logger.info(f"Total de {total_count} leads para processar")
        
        # Prepara a lista para processamento em massa
        leads_data = []
        
        # Itera sobre cada linha e prepara os dados
        for idx, row in df.iterrows():
            # Prepara os dados do lead para o Salesforce
            lead_data = {}
            
            # Mapeia cada coluna do Salesforce, garantindo que exista
            for field in ["LastName", "FirstName", "Company", "Email", "Phone", 
                        "Title", "Street", "City", "State", "PostalCode", 
                        "Country", "LeadSource"]:
                if field in df.columns and not pd.isna(row[field]):
                    lead_data[field] = str(row[field]).strip()
            
            # Verifica campos obrigatórios
            if "LastName" not in lead_data or not lead_data["LastName"]:
                logger.warning(f"Linha {idx+1}: Campo obrigatório LastName vazio ou ausente")
                lead_data["LastName"] = "Lead Sem Nome"  # Valor padrão para evitar falha
                
            if "Company" not in lead_data or not lead_data["Company"]:
                logger.warning(f"Linha {idx+1}: Campo obrigatório Company vazio ou ausente")
                lead_data["Company"] = "Empresa Desconhecida"  # Valor padrão para evitar falha
                
            # Garantir que o nome da companhia não ultrapasse 255 caracteres
            if "Company" in lead_data and len(lead_data["Company"]) > 255:
                lead_data["Company"] = lead_data["Company"][:255]
                
            # Email precisa estar em um formato válido
            if "Email" in lead_data:
                # Limpar o email de espaços e garantir que é lowercase
                lead_data["Email"] = lead_data["Email"].strip().lower()
                
            # Telefone deve estar em formato numérico limpo
            if "Phone" in lead_data:
                lead_data["Phone"] = clean_phone_number(lead_data["Phone"])
                
            # Certificar-se de que todos os valores são strings
            for key in lead_data.keys():
                if lead_data[key] is not None and not isinstance(lead_data[key], str):
                    lead_data[key] = str(lead_data[key])
                
            # Adiciona informação de atribuição apenas se um ID de proprietário válido for fornecido
            if owner_id and owner_id.strip():
                if len(owner_id) >= 15 and owner_id.startswith('00'):
                    lead_data["OwnerId"] = owner_id
            
            # Adiciona à lista de leads para processamento em massa
            leads_data.append(lead_data)
        
        if not leads_data:
            logger.warning("Nenhum lead válido encontrado para processamento")
            return False, "Nenhum lead válido encontrado para processamento"
        
        # Define tamanho máximo de lote para processamento
        batch_size = 2000  # Recomendado pelo Salesforce para melhor desempenho
        total_success = 0
        all_results = []
        
        # Processa em lotes de batch_size registros
        for i in range(0, len(leads_data), batch_size):
            batch = leads_data[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(leads_data) + batch_size - 1) // batch_size
            
            logger.info(f"Processando lote {batch_num} de {total_batches} ({len(batch)} registros)")
            
            # Chama a API em massa para este lote
            batch_results = create_bulk_leads_in_salesforce(batch)
            
            if batch_results:
                total_success += batch_results['success_count']
                
                # Processa resultados para formatação consistente com a interface atual
                for success_record in batch_results.get('successful_records', []):
                    # Encontra o índice original do registro
                    orig_idx = i + success_record.get('index', 0)
                    if 0 <= orig_idx < len(leads_data):
                        lead_data = leads_data[orig_idx]
                        result = {
                            'success': True,
                            'id': success_record.get('sf_id'),
                            'name': lead_data.get('LastName', 'Sem nome'),
                            'email': lead_data.get('Email', ''),
                            'errors': []
                        }
                        all_results.append(result)
                
                for failed_record in batch_results.get('failed_records', []):
                    # Encontra o índice original do registro
                    orig_idx = i + failed_record.get('index', 0)
                    if 0 <= orig_idx < len(leads_data):
                        lead_data = leads_data[orig_idx]
                        result = {
                            'success': False,
                            'id': None,
                            'name': lead_data.get('LastName', 'Sem nome'),
                            'email': lead_data.get('Email', ''),
                            'errors': [failed_record.get('error', 'Erro desconhecido')]
                        }
                        all_results.append(result)
            else:
                # Falha completa do lote - registra cada item como falha
                for j, lead_data in enumerate(batch):
                    result = {
                        'success': False,
                        'id': None,
                        'name': lead_data.get('LastName', f'Lead #{i+j+1}'),
                        'email': lead_data.get('Email', ''),
                        'errors': ['Falha ao processar lote no Salesforce']
                    }
                    all_results.append(result)
            
        # Log do resultado final consolidado
        logger.info(f"Processamento em massa concluído. {total_success} de {total_count} leads criados com sucesso.")
        
        # Verifica se todos os registros foram processados
        if len(all_results) < total_count:
            logger.warning(f"Discrepância nos resultados: {len(all_results)} resultados para {total_count} leads processados")
            # Adiciona resultados faltantes para manter a contagem correta
            missing_count = total_count - len(all_results)
            for _ in range(missing_count):
                all_results.append({
                    'success': False,
                    'id': None,
                    'name': 'Lead não processado',
                    'email': '',
                    'errors': ['Lead não processado pelo Salesforce']
                })
        
        # Garante que pelo menos temos um resultado, mesmo que seja de erro
        if not all_results and total_count > 0:
            all_results = [{
                'success': False,
                'id': None,
                'name': 'Erro de processamento',
                'email': '',
                'errors': ['Falha ao processar os leads no Salesforce']
            }]
        
        # Se pelo menos um lead foi bem-sucedido, consideramos a operação como um todo bem-sucedida
        # mas enviamos todos os resultados para que o app possa mostrar detalhes das falhas
        logger.info(f"Resultado final: {total_success} sucessos de {total_count} leads")
        return total_success > 0, all_results
        
    except Exception as e:
        logger.exception(f"Erro ao criar leads em massa a partir do CSV: {str(e)}")
        return False, str(e)

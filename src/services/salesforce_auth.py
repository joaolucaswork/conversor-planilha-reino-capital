"""
Módulo para autenticação com Salesforce.
Gerencia o processo de autenticação OAuth com o Salesforce.
"""

import os
import requests
import json
from src.utils.salesforce_logger import get_salesforce_logger

# Configuração do logger
logger = get_salesforce_logger('salesforce_auth')

def get_salesforce_access_token():
    """
    Obtém um token de acesso OAuth para o Salesforce usando credenciais.
    Seleciona automaticamente o conjunto de credenciais baseado na
    variável de ambiente SALESFORCE_ENVIRONMENT.
    
    Returns:
        str: Token de acesso ou None em caso de falha.
    """
    logger.info("Iniciando obtenção de token de acesso do Salesforce")
    
    # Determina o ambiente (produção ou sandbox)
    environment = os.getenv('SALESFORCE_ENVIRONMENT', 'sandbox').lower()
    
    # Seleciona o prefixo correto baseado no ambiente
    prefix = 'PRODUCTION_' if environment == 'production' else 'SANDBOX_'
    
    logger.info(f"Usando ambiente: {environment.upper()}")
    
    # Obtém as credenciais do ambiente selecionado
    client_id = os.getenv(f'{prefix}CLIENT_ID')
    client_secret = os.getenv(f'{prefix}CLIENT_SECRET')
    username = os.getenv(f'{prefix}USERNAME')
    password = os.getenv(f'{prefix}PASSWORD')
    security_token = os.getenv(f'{prefix}SECURITY_TOKEN', '')
    instance_url = os.getenv(f'{prefix}INSTANCE_URL')
    
    # Verifica se as variáveis de ambiente necessárias estão definidas
    required_vars = {
        f'{prefix}CLIENT_ID': client_id,
        f'{prefix}CLIENT_SECRET': client_secret,
        f'{prefix}USERNAME': username,
        f'{prefix}PASSWORD': password,
        f'{prefix}INSTANCE_URL': instance_url
    }
    
    missing_vars = [var for var, value in required_vars.items() if not value]
    
    if missing_vars:
        logger.error(f"Variáveis de ambiente obrigatórias não definidas: {', '.join(missing_vars)}")
        return None
    
    # Define a URL de autenticação com base no ambiente
    if environment == 'production':
        auth_url = 'https://login.salesforce.com/services/oauth2/token'
        logger.info("Usando endpoint de produção para autenticação")
    else:
        auth_url = 'https://test.salesforce.com/services/oauth2/token'
        logger.info("Usando endpoint de sandbox para autenticação")
    
    # Prepara os dados para a requisição de autenticação
    auth_data = {
        'grant_type': 'password',
        'client_id': client_id,
        'client_secret': client_secret,
        'username': username,
        'password': password + security_token
    }
    
    try:
        # Faz a requisição de autenticação
        logger.debug(f"Enviando requisição de autenticação para: {auth_url}")
        response = requests.post(auth_url, data=auth_data)
        
        # Verifica se a requisição foi bem-sucedida
        if response.status_code == 200:
            # Extrai o token de acesso da resposta
            auth_response = response.json()
            access_token = auth_response.get('access_token')
            response_instance_url = auth_response.get('instance_url')
            
            # Verifica se a URL da instância corresponde à configurada
            if response_instance_url != instance_url:
                logger.warning(f"URL da instância na resposta ({response_instance_url}) é diferente da configurada ({instance_url})")
            
            # Define a URL da instância para uso em outras partes da aplicação
            os.environ['SALESFORCE_INSTANCE_URL'] = instance_url
            
            logger.info("Token de acesso obtido com sucesso")
            logger.debug(f"Instance URL: {instance_url}")
            
            # Configurar a versão da API corretamente
            api_version = os.getenv('SALESFORCE_API_VERSION', '63.0')
            if not api_version.startswith('v'):
                api_version = f"v{api_version}"
                os.environ['SALESFORCE_API_VERSION'] = api_version
            
            # Retorna apenas o token de acesso
            return access_token
        else:
            # Registra o erro em caso de falha
            logger.error(f"Erro na autenticação. Status: {response.status_code}")
            logger.error(f"Resposta: {response.text}")
            return None
    
    except Exception as e:
        # Captura e registra qualquer exceção que ocorra durante o processo
        logger.exception(f"Exceção ao obter token de acesso: {str(e)}")
        return None

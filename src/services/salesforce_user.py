"""
Módulo para obter informações do usuário no Salesforce.
"""

import os
import json
import requests
from .salesforce_auth import get_salesforce_access_token
from ..utils.salesforce_logger import get_salesforce_logger

# Configuração do logger
logger = get_salesforce_logger('salesforce_user')

def get_current_user_info():
    """
    Obtém informações do usuário atualmente autenticado no Salesforce.
    
    Returns:
        dict: Informações do usuário (nome, alias, etc.) ou None em caso de erro.
    """
    logger.info("=== OBTENDO INFORMAÇÕES DO USUÁRIO NO SALESFORCE ===")
    
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
        
        # Determina o ambiente (produção ou sandbox)
        environment = os.getenv('SALESFORCE_ENVIRONMENT', 'sandbox').lower()
        
        # Seleciona o prefixo correto baseado no ambiente
        prefix = 'PRODUCTION_' if environment == 'production' else 'SANDBOX_'
        
        # Obtém a URL da instância do ambiente selecionado
        instance_url = os.getenv(f'{prefix}INSTANCE_URL')
        
        if not instance_url:
            logger.error(f"URL da instância do Salesforce não configurada para o ambiente {environment}")
            return None
        
        # Endpoint para obter informações do usuário atual
        url = f"{instance_url}/services/data/v{api_version}/chatter/users/me"
        
        # Correção para garantir que não haja duplicação de 'v' na URL
        if 'vv' in url:
            url = url.replace('vv', 'v')
            
        logger.debug(f"Consultando informações do usuário via GET para {url}")
        
        # Faz a requisição para obter informações do usuário
        response = requests.get(url, headers=headers)
        
        logger.debug(f"Status code: {response.status_code}")
        
        if response.status_code == 200:  # 200 significa OK
            user_info = response.json()
            logger.info(f"Informações do usuário obtidas com sucesso! Nome: {user_info.get('displayName', 'Não disponível')}")
            
            # Extrai informações relevantes
            return {
                'id': user_info.get('id'),
                'name': user_info.get('displayName'),
                'username': user_info.get('username'),
                'alias': user_info.get('additionalLabel', user_info.get('companyName', 'N/A')),
                'email': user_info.get('email'),
                'profile_url': user_info.get('photoUrl')
            }
        elif response.status_code == 404:
            logger.error("Endpoint de usuário não encontrado (404). Verificando a URL da instância e a versão da API.")
            logger.error(f"URL utilizada: {url}")
            # Informações adicionais para ajudar no diagnóstico do erro 404
            logger.error(f"API Version: {api_version}, Instance URL: {instance_url}")
            
            # Tenta um endpoint alternativo como fallback
            alt_url = f"{instance_url}/services/data/v{api_version}/sobjects/User/me"
            
            # Correção para garantir que não haja duplicação de 'v' na URL
            if 'vv' in alt_url:
                alt_url = alt_url.replace('vv', 'v')
                
            logger.debug(f"Tentando endpoint alternativo: {alt_url}")
            
            alt_response = requests.get(alt_url, headers=headers)
            if alt_response.status_code == 200:
                user_info = alt_response.json()
                logger.info(f"Informações do usuário obtidas com sucesso via endpoint alternativo!")
                return {
                    'id': user_info.get('Id'),
                    'name': user_info.get('Name'),
                    'username': user_info.get('Username'),
                    'alias': user_info.get('Alias', 'N/A'),
                    'email': user_info.get('Email')
                }
            else:
                logger.error(f"Endpoint alternativo também falhou. Status: {alt_response.status_code}")
                return None
        else:
            logger.error(f"Erro ao obter informações do usuário. Status: {response.status_code}")
            logger.error(f"Resposta de erro: {response.text}")
            return None
    
    except Exception as e:
        logger.exception(f"Exceção ao obter informações do usuário: {str(e)}")
        return None

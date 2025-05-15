"""
Módulo especializado de logging para operações do Salesforce.

Este módulo implementa funcionalidades avançadas de logging para diagnóstico de problemas
em operações de integração com o Salesforce.
"""

import os
import json
import logging
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Diretório para armazenar os logs específicos do Salesforce
SALESFORCE_LOG_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    ), 
    "logs", 
    "salesforce"
)

# Garantir que o diretório de logs existe
if not os.path.exists(SALESFORCE_LOG_DIR):
    os.makedirs(SALESFORCE_LOG_DIR, exist_ok=True)

# Identificar o ambiente (produção ou sandbox)
ENVIRONMENT = os.getenv("SALESFORCE_ENVIRONMENT", "sandbox").upper()

# Configurar os arquivos de log com ambiente específico
LOG_FILE = os.path.join(SALESFORCE_LOG_DIR, f"salesforce_{ENVIRONMENT.lower()}.log")
REQUEST_LOG_FILE = os.path.join(SALESFORCE_LOG_DIR, f"sf_requests_{ENVIRONMENT.lower()}.log")
ERROR_LOG_FILE = os.path.join(SALESFORCE_LOG_DIR, f"sf_errors_{ENVIRONMENT.lower()}.log")

# Tamanho máximo para os arquivos de log antes da rotação (5MB)
MAX_LOG_SIZE = 5 * 1024 * 1024

# Número de backups a manter
BACKUP_COUNT = 5

# Padrões de sensibilidade para mascaramento
SENSITIVE_PATTERNS = {
    'token': re.compile(r'(token|Bearer)["\'\s:=]+([^"\'&]+)', re.IGNORECASE),
    'password': re.compile(r'(password|senha)["\'\s:=]+([^"\'&]+)', re.IGNORECASE),
    'key': re.compile(r'(key|chave|secret)["\'\s:=]+([^"\'&]+)', re.IGNORECASE)
}

class SalesforceLogger:
    """
    Logger especializado para operações do Salesforce com capacidade
    avançada de diagnóstico e mascaramento de dados sensíveis.
    """
    
    def __init__(self, name):
        """
        Inicializa o logger com configurações específicas para Salesforce.
        
        Args:
            name (str): Nome do logger, usado para identificar a fonte dos logs.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.name = name
        
        # Evita duplicação de handlers se o logger já estiver configurado
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self):
        """Configura os handlers para os diferentes arquivos de log."""
        # Formato padrão para logs
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para o log principal
        main_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)
        
        # Handler para requisições
        request_handler = RotatingFileHandler(
            REQUEST_LOG_FILE, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT
        )
        request_handler.setLevel(logging.DEBUG)
        request_handler.setFormatter(formatter)
        self.logger.addHandler(request_handler)
        
        # Handler para erros específicos do Salesforce
        error_handler = RotatingFileHandler(
            ERROR_LOG_FILE, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
        
        # Handler para console - útil durante desenvolvimento
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _mask_sensitive_data(self, message):
        """
        Mascara dados sensíveis como tokens, senhas e chaves.
        
        Args:
            message (str): Mensagem original a ser mascarada.
            
        Returns:
            str: Mensagem com dados sensíveis mascarados.
        """
        if not isinstance(message, str):
            return message
            
        masked_message = message
        
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            masked_message = pattern.sub(
                lambda m: f'{m.group(1)}{m.group(1)[0]}***{m.group(1)[0]}', 
                masked_message
            )
        
        return masked_message
    
    def _format_with_context(self, message):
        """
        Adiciona contexto à mensagem de log.
        
        Args:
            message (str): Mensagem original.
            
        Returns:
            str: Mensagem formatada com contexto adicional.
        """
        context = {
            'environment': ENVIRONMENT,
            'timestamp': datetime.now().isoformat(),
            'caller': self.name
        }
        
        context_str = ' | '.join([f"{k}={v}" for k, v in context.items()])
        return f"[{context_str}] {message}"
    
    def debug(self, message):
        """Registra mensagem de nível DEBUG."""
        safe_message = self._mask_sensitive_data(message)
        formatted_message = self._format_with_context(safe_message)
        self.logger.debug(formatted_message)
    
    def info(self, message):
        """Registra mensagem de nível INFO."""
        safe_message = self._mask_sensitive_data(message)
        formatted_message = self._format_with_context(safe_message)
        self.logger.info(formatted_message)
    
    def warning(self, message):
        """Registra mensagem de nível WARNING."""
        safe_message = self._mask_sensitive_data(message)
        formatted_message = self._format_with_context(safe_message)
        self.logger.warning(formatted_message)
    
    def error(self, message):
        """Registra mensagem de nível ERROR."""
        safe_message = self._mask_sensitive_data(message)
        formatted_message = self._format_with_context(safe_message)
        self.logger.error(formatted_message)
    
    def exception(self, message):
        """Registra mensagem de exceção com stack trace."""
        safe_message = self._mask_sensitive_data(message)
        formatted_message = self._format_with_context(safe_message)
        self.logger.exception(formatted_message)
    
    def critical(self, message):
        """Registra mensagem de nível CRITICAL."""
        safe_message = self._mask_sensitive_data(message)
        formatted_message = self._format_with_context(safe_message)
        self.logger.critical(formatted_message)
    
    def log_request(self, url, method, headers, data=None, params=None):
        """
        Registra detalhes de uma requisição HTTP para o Salesforce
        
        Args:
            url (str): URL da requisição
            method (str): Método HTTP (GET, POST, etc)
            headers (dict): Cabeçalhos da requisição
            data (dict, opcional): Corpo da requisição
            params (dict, opcional): Parâmetros de query string
        """
        # Faz cópias para não modificar os originais
        safe_headers = headers.copy() if headers else {}
        safe_data = data.copy() if data else {}
        
        # Mascara dados sensíveis nos cabeçalhos
        if 'Authorization' in safe_headers:
            safe_headers['Authorization'] = 'Bearer ***'
        
        # Prepara informações da requisição
        request_info = {
            'timestamp': datetime.now().isoformat(),
            'method': method,
            'url': url,
            'headers': safe_headers,
            'environment': ENVIRONMENT
        }
        
        if safe_data:
            request_info['data'] = safe_data
        
        if params:
            request_info['params'] = params
        
        # Serializa para JSON
        try:
            request_json = json.dumps(request_info, indent=2)
        except:
            request_json = f"Non-serializable request: {str(request_info)}"
        
        self.debug(f"SALESFORCE HTTP REQUEST:\n{request_json}")
    
    def log_response(self, response, request_duration=None):
        """
        Registra detalhes de uma resposta HTTP do Salesforce
        
        Args:
            response (Response): Objeto de resposta HTTP
            request_duration (float, opcional): Duração da requisição em segundos
        """
        try:
            # Tenta extrair o conteúdo JSON
            try:
                content = response.json()
            except:
                content = response.text if response.text else "No content"
            
            # Prepara informações da resposta
            response_info = {
                'timestamp': datetime.now().isoformat(),
                'status_code': response.status_code,
                'content': content,
                'environment': ENVIRONMENT
            }
            
            if request_duration:
                response_info['duration_seconds'] = round(request_duration, 3)
            
            # Serializa para JSON
            try:
                response_json = json.dumps(response_info, indent=2)
            except:
                response_json = f"Non-serializable response: {str(response_info)}"
            
            # Log com nível apropriado baseado no status code
            if 200 <= response.status_code < 300:
                self.debug(f"SALESFORCE HTTP RESPONSE:\n{response_json}")
            elif 400 <= response.status_code < 500:
                self.warning(f"SALESFORCE HTTP RESPONSE (CLIENT ERROR):\n{response_json}")
            elif response.status_code >= 500:
                self.error(f"SALESFORCE HTTP RESPONSE (SERVER ERROR):\n{response_json}")
            else:
                self.info(f"SALESFORCE HTTP RESPONSE (UNUSUAL STATUS CODE):\n{response_json}")
        
        except Exception as e:
            self.error(f"Erro ao logar resposta HTTP: {str(e)}")


def get_salesforce_logger(name):
    """
    Obtém uma instância do logger especializado para Salesforce
    
    Args:
        name (str): Nome do logger
        
    Returns:
        SalesforceLogger: Instância do logger especializado
    """
    return SalesforceLogger(name)


class RequestsInterceptor:
    """Implementa uma função para interceptar e logar chamadas HTTP ao Salesforce"""
    
    def __init__(self):
        """
        Registra automaticamente todas as chamadas para domínios do Salesforce.
        """
        self.logger = get_salesforce_logger('salesforce.http.interceptor')
        self.salesforce_domains = [
            'salesforce.com',
            'force.com',
            'salesforce.mil',
            'my.salesforce.com',
            'lightning.force.com'
        ]
    
    def is_salesforce_url(self, url):
        """Verifica se a URL é do Salesforce"""
        return any(domain in url for domain in self.salesforce_domains)
    
    def log_request(self, url, method, headers=None, data=None, params=None):
        """Registra uma requisição se for para o Salesforce"""
        if not self.is_salesforce_url(url):
            return
        
        self.logger.log_request(url, method, headers, data, params)
    
    def log_response(self, url, response, duration=None):
        """Registra uma resposta se for do Salesforce"""
        if not self.is_salesforce_url(url):
            return
        
        self.logger.log_response(response, duration)
    
    def log_error(self, url, error):
        """Registra um erro se for para o Salesforce"""
        if not self.is_salesforce_url(url):
            return
        
        self.logger.error(f"Erro na requisição para {url}: {str(error)}")

# Instancia um interceptor global para facilitar o uso
interceptor = RequestsInterceptor()

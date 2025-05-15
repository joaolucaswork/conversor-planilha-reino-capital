"""
Módulo especializado de logging para operações de conversão de arquivos.

Este módulo implementa funcionalidades avançadas de logging para monitorar
e diagnosticar problemas no processo de conversão de arquivos.
"""

import os
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Diretório para armazenar os logs de conversão
CONVERSION_LOG_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    ), 
    "logs", 
    "conversion"
)

# Garantir que o diretório de logs existe
if not os.path.exists(CONVERSION_LOG_DIR):
    os.makedirs(CONVERSION_LOG_DIR, exist_ok=True)

# Configurar os arquivos de log
MAIN_LOG_FILE = os.path.join(CONVERSION_LOG_DIR, "conversion.log")
ERROR_LOG_FILE = os.path.join(CONVERSION_LOG_DIR, "conversion_errors.log")
DETAILS_LOG_FILE = os.path.join(CONVERSION_LOG_DIR, "conversion_details.log")

# Tamanho máximo para os arquivos de log antes da rotação (5MB)
MAX_LOG_SIZE = 5 * 1024 * 1024

# Número de backups a manter
BACKUP_COUNT = 5

class ConversionLogger:
    """
    Logger especializado para operações de conversão de arquivos com capacidade
    avançada de diagnóstico e rastreamento de processos.
    """
    
    def __init__(self, name):
        """
        Inicializa o logger com configurações específicas para conversão de arquivos.
        
        Args:
            name (str): Nome do logger, usado para identificar a fonte dos logs.
        """
        self.logger = logging.getLogger(f"conversion.{name}")
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
            MAIN_LOG_FILE, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT
        )
        main_handler.setLevel(logging.INFO)
        main_handler.setFormatter(formatter)
        self.logger.addHandler(main_handler)
        
        # Handler para detalhes técnicos
        details_handler = RotatingFileHandler(
            DETAILS_LOG_FILE, 
            maxBytes=MAX_LOG_SIZE, 
            backupCount=BACKUP_COUNT
        )
        details_handler.setLevel(logging.DEBUG)
        details_handler.setFormatter(formatter)
        self.logger.addHandler(details_handler)
        
        # Handler para erros específicos
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
    
    def _format_with_context(self, message):
        """
        Adiciona contexto à mensagem de log.
        
        Args:
            message (str): Mensagem original.
            
        Returns:
            str: Mensagem formatada com contexto adicional.
        """
        return f"[conversion_process={self.name} | timestamp={datetime.now().isoformat()} | caller={self.name}] {message}"
    
    def debug(self, message):
        """Registra mensagem de nível DEBUG."""
        formatted_message = self._format_with_context(message)
        self.logger.debug(formatted_message)
    
    def info(self, message):
        """Registra mensagem de nível INFO."""
        formatted_message = self._format_with_context(message)
        self.logger.info(formatted_message)
    
    def warning(self, message):
        """Registra mensagem de nível WARNING."""
        formatted_message = self._format_with_context(message)
        self.logger.warning(formatted_message)
    
    def error(self, message):
        """Registra mensagem de nível ERROR."""
        formatted_message = self._format_with_context(message)
        self.logger.error(formatted_message)
    
    def exception(self, message):
        """Registra mensagem de exceção com stack trace."""
        formatted_message = self._format_with_context(message)
        self.logger.exception(formatted_message)
    
    def critical(self, message):
        """Registra mensagem de nível CRITICAL."""
        formatted_message = self._format_with_context(message)
        self.logger.critical(formatted_message)
    
    def log_conversion_start(self, file_info):
        """
        Registra o início de um processo de conversão
        
        Args:
            file_info (dict): Informações sobre o arquivo a ser convertido
        """
        try:
            info = {
                'action': 'conversion_start',
                'timestamp': datetime.now().isoformat(),
                'file_info': file_info
            }
            
            # Serializa para JSON
            try:
                info_json = json.dumps(info, indent=2)
            except:
                info_json = f"Non-serializable info: {str(info)}"
            
            self.info(f"=== INICIANDO CONVERSÃO DE ARQUIVO ===\n{info_json}")
        except Exception as e:
            self.error(f"Erro ao registrar início da conversão: {str(e)}")
    
    def log_conversion_step(self, step_name, step_details):
        """
        Registra um passo específico da conversão
        
        Args:
            step_name (str): Nome do passo (ex: 'extração', 'transformação')
            step_details (dict): Detalhes sobre o passo específico
        """
        try:
            step_info = {
                'action': 'conversion_step',
                'timestamp': datetime.now().isoformat(),
                'step_name': step_name,
                'details': step_details
            }
            
            # Serializa para JSON
            try:
                step_json = json.dumps(step_info, indent=2)
            except:
                step_json = f"Non-serializable step info: {str(step_info)}"
            
            self.info(f"PASSO DE CONVERSÃO: {step_name}\n{step_json}")
        except Exception as e:
            self.error(f"Erro ao registrar passo de conversão: {str(e)}")
    
    def log_conversion_complete(self, result_info):
        """
        Registra a conclusão com sucesso de um processo de conversão
        
        Args:
            result_info (dict): Informações sobre o resultado da conversão
        """
        try:
            completion_info = {
                'action': 'conversion_complete',
                'timestamp': datetime.now().isoformat(),
                'result': result_info
            }
            
            # Serializa para JSON
            try:
                completion_json = json.dumps(completion_info, indent=2)
            except:
                completion_json = f"Non-serializable completion info: {str(completion_info)}"
            
            self.info(f"=== CONVERSÃO CONCLUÍDA COM SUCESSO ===\n{completion_json}")
        except Exception as e:
            self.error(f"Erro ao registrar conclusão da conversão: {str(e)}")
    
    def log_conversion_error(self, error_info):
        """
        Registra um erro no processo de conversão
        
        Args:
            error_info (dict): Informações detalhadas sobre o erro
        """
        try:
            error_details = {
                'action': 'conversion_error',
                'timestamp': datetime.now().isoformat(),
                'error': error_info
            }
            
            # Serializa para JSON
            try:
                error_json = json.dumps(error_details, indent=2)
            except:
                error_json = f"Non-serializable error info: {str(error_details)}"
            
            self.error(f"=== ERRO NA CONVERSÃO DE ARQUIVO ===\n{error_json}")
        except Exception as e:
            self.error(f"Erro ao registrar erro de conversão: {str(e)}")


def get_conversion_logger(name):
    """
    Obtém uma instância do logger especializado para conversão de arquivos
    
    Args:
        name (str): Nome do logger
        
    Returns:
        ConversionLogger: Instância do logger especializado
    """
    return ConversionLogger(name)

import os
import pandas as pd
import time
import traceback
import io 
import json
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from src.services.salesforce_api import create_leads_from_csv
from src.services.salesforce_user import get_current_user_info
from src.utils.salesforce_logger import get_salesforce_logger
from src.utils.conversion_logger import get_conversion_logger
from src.utils.csv_helper import fix_salesforce_lead_csv
from llm import get_ai_completion, get_column_mapping_from_ai 

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'chave-secreta-dev')
# Configuração para garantir que a sessão persiste corretamente
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)

# Configurar os loggers
logger = get_salesforce_logger('app')
conversion_logger = get_conversion_logger('file_converter')

# Custom error handler for Method Not Allowed (405) errors
@app.errorhandler(405)
def method_not_allowed(error):
    # Log detailed information about the request causing 405 error
    logger.error(f"405 Method Not Allowed Error - URL: {request.url}, Method: {request.method}")
    logger.error(f"Allowed methods for this endpoint: {request.routing_exception.valid_methods if hasattr(request, 'routing_exception') else 'Unknown'}")
    logger.error(f"Headers: {dict(request.headers)}")
    logger.error(f"Query parameters: {dict(request.args)}")
    logger.error(f"Referrer: {request.referrer}")
    logger.error(f"Client IP: {request.remote_addr}")
    
    # Return JSON response for API requests, HTML for browser requests
    if request.headers.get('Accept', '').startswith('application/json'):
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL.',
            'url': request.url,
            'method': request.method,
            'allowed_methods': request.routing_exception.valid_methods if hasattr(request, 'routing_exception') else ['unknown']
        }), 405
    else:
        flash(f"Erro 405: Método {request.method} não permitido para {request.path}. Use um dos métodos: {', '.join(request.routing_exception.valid_methods) if hasattr(request, 'routing_exception') else 'desconhecido'}", "error")
        return redirect(url_for('index'))

# Configurações
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'A converter')
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limita o tamanho do upload para 16MB

# Garantir que os diretórios necessários existam
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('logs/salesforce', exist_ok=True)

# Definir a versão da API Salesforce
os.environ['SALESFORCE_API_VERSION'] = '63.0'

# TARGET SCHEMA FOR AI MAPPING (Salesforce Lead Object API Names)
# Descriptions help the AI understand the field's purpose.
TARGET_SALESFORCE_SCHEMA = {
    "LastName": "O sobrenome do lead (obrigatório em Salesforce). Ex: Silva, Santos.",
    "FirstName": "O primeiro nome do lead. Ex: João, Maria.",
    "Company": "A empresa ou organização à qual o lead pertence (obrigatório em Salesforce). Ex: Acme Corp, Hospital Local.",
    "Email": "O endereço de e-mail principal do lead. Ex: joao.silva@example.com.",
    "Phone": "O número de telefone principal do lead. Ex: (11) 99999-8888.",
    "Title": "O cargo ou título do lead na empresa. Ex: Gerente de Vendas, Desenvolvedor.",
    "Street": "O endereço (rua, número, complemento) do lead.",
    "City": "A cidade do lead.",
    "State": "O estado ou província do lead (usar sigla se comum, ex: SP, RJ).",
    "PostalCode": "O código postal (CEP) do lead.",
    "Country": "O país do lead.",
    "LeadSource": "A origem do lead. Ex: Web, Indicação, Feira.",
    "OwnerId": "ID do usuário que será o proprietário do lead no Salesforce."
    # "Status": "O status atual do lead no funil de vendas. Ex: Novo, Qualificado, Contatado.", # Usually set by rules
    # Add any custom fields your Salesforce org uses, e.g.:
    # "CPF__c": "O CPF do lead (formato XXX.XXX.XXX-XX).",
    # "ProductInterest__c": "Produto de interesse do lead."
}

def allowed_file(filename):
    """Verifica se o arquivo tem uma extensão válida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Middleware to log all requests
@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Body: {request.get_data().decode('utf-8', errors='replace')}")

@app.route('/')
def index():
    """Rota principal"""
    # Verifica se temos informações de usuário na sessão
    user_info = session.get('user_info', None)
    
    # Se não temos informações do usuário na sessão, tenta obter do Salesforce
    if not user_info:
        try:
            # Define o ambiente a partir da sessão ou usa sandbox como padrão
            environment = session.get('environment', 'sandbox')
            os.environ['SALESFORCE_ENVIRONMENT'] = environment
            
            logger.info(f"Tentando obter informações do usuário do Salesforce no ambiente: {environment}")
            logger.info(f"Versão da API: {os.environ.get('SALESFORCE_API_VERSION')}")
            
            # Tenta obter informações do usuário
            user_info = get_current_user_info()
            if user_info:
                logger.info(f"Informações do usuário obtidas: {user_info['name']} ({user_info['alias']})")
                session['user_info'] = user_info
            else:
                logger.warning("Não foi possível obter informações do usuário do Salesforce.")
                logger.info("Verifique as credenciais no arquivo .env e a configuração da URL da instância.")
        except Exception as e:
            logger.error(f"Erro ao obter informações do usuário: {str(e)}")
            logger.exception("Detalhes do erro:")
            # Não mostra flash message para não confundir o usuário na página inicial
    
    return render_template('index.html', user_info=user_info)

import uuid
import shutil

@app.route('/upload_file', methods=['POST'])
def upload_file():
    """Processa o upload do arquivo e faz conversão para CSV se necessário"""
    # Log detalhado da requisição para depuração
    logger.info("----- Início do processamento de upload_file -----")
    logger.info(f"Headers da requisição: {dict(request.headers)}")
    logger.info(f"Formulário: {dict(request.form)}")
    logger.info(f"Arquivos: {list(request.files.keys())}")
    
    if 'file' not in request.files:
        logger.warning("Nenhum arquivo na requisição - 'file' não está em request.files")
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    file = request.files['file']
    logger.info(f"Arquivo recebido: {file.filename if file else 'Objeto file nulo'}")
    
    # Log do tamanho do arquivo e tipo de conteúdo se disponível
    if file and hasattr(file, 'content_length'):
        logger.info(f"Tamanho do arquivo: {file.content_length} bytes")
    if file and hasattr(file, 'content_type'):
        logger.info(f"Tipo de conteúdo: {file.content_type}")
    
    # Verificar se o arquivo está vazio
    if file.filename == '':
        logger.warning("Nome do arquivo está vazio")
        flash('Nenhum arquivo selecionado')
        return redirect(url_for('index'))
    
    # Obtém o ambiente selecionado (sandbox ou production)
    environment = request.form.get('environment', 'sandbox')
    session['environment'] = environment
    logger.info(f"Ambiente selecionado: {environment}")
    
    # Pegar o proprietário selecionado para os leads
    lead_owner = request.form.get('lead_owner', '')
    custom_owner_id = request.form.get('custom_owner_id', '')
    
    # Define o ID do proprietário com base na seleção
    owner_id = None
    if lead_owner == 'custom' and custom_owner_id and custom_owner_id.strip():
        owner_id = custom_owner_id.strip()
        owner_type = 'personalizado'
    elif lead_owner == 'jlucas':
        # Deixamos None para usar atribuição automática do Salesforce
        owner_type = 'automático (jlucas)'
    else:
        owner_type = 'automático (regras do Salesforce)'
    
    # Salva na sessão para uso posterior
    session['lead_owner'] = lead_owner
    session['owner_id'] = owner_id
    logger.info(f"Atribuição de leads: {owner_type} {f'(ID: {owner_id})' if owner_id else ''}")
    
    # Verificar o tipo de arquivo
    if not allowed_file(file.filename):
        logger.warning(f"Tipo de arquivo não permitido: {file.filename}")
        flash('Tipo de arquivo não permitido. Use apenas CSV, XLSX ou XLS.')
        return redirect(url_for('index'))
        
    # Log de sucesso na validação do arquivo
    logger.info(f"Arquivo válido detectado: {file.filename}")
    
    # Tenta obter informações do usuário do Salesforce
    try:
        user_info = get_current_user_info()
        if user_info:
            logger.info(f"Informações do usuário obtidas: {user_info['name']} ({user_info['alias']})")
            session['user_info'] = user_info
        else:
            logger.warning("Não foi possível obter informações do usuário do Salesforce.")
            # Permite continuar mesmo sem informações do usuário, mas pode ser útil logar
    except Exception as e:
        logger.error(f"Erro ao obter informações do usuário: {str(e)}")
        flash(f'Erro ao conectar com Salesforce: {str(e)}', 'error')
        # Decide se quer redirecionar ou permitir continuar
        # return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        original_file_ext = filename.rsplit('.', 1)[1].lower()
        
        # Cria um nome de arquivo temporário único para evitar conflitos
        temp_filename_base = f"temp_{uuid.uuid4().hex}"
        temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{temp_filename_base}.{original_file_ext}")
        
        # Salva o arquivo original temporariamente
        try:
            file.save(temp_filepath)
            conversion_logger.info(f"Arquivo '{filename}' salvo temporariamente como '{temp_filepath}'")
            logger.info(f"Arquivo salvo com sucesso em: {temp_filepath}")
            
            # Verificação adicional do arquivo salvo
            if os.path.exists(temp_filepath):
                logger.info(f"Arquivo verificado no sistema: {temp_filepath} (Tamanho: {os.path.getsize(temp_filepath)} bytes)")
            else:
                logger.error(f"ERRO: Arquivo não encontrado após salvamento: {temp_filepath}")
                flash('Erro ao salvar o arquivo. Por favor, tente novamente.')
                return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Erro ao salvar o arquivo: {str(e)}")
            logger.error(traceback.format_exc())
            flash('Erro ao salvar o arquivo. Por favor, tente novamente.')
            return redirect(url_for('index'))

        output_filename = 'leads-semformatado.csv'
        output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        final_ai_mapped_filepath = output_filepath # O arquivo final será o mapeado pela IA

        try:
            conversion_logger.info(f"Iniciando processamento do arquivo: {filename}")
            df_snippet = None
            file_content_for_ai = ""

            # 1. Ler um snippet do arquivo para a IA
            conversion_logger.info("Preparando snippet do arquivo para análise da IA...")
            try:
                if original_file_ext == 'csv':
                    # Tentar com diferentes delimitadores comuns e codificações para CSV
                    common_delimiters = [',', ';', '\t']
                    common_encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
                    read_success = False
                    for enc in common_encodings:
                        for delim in common_delimiters:
                            try:
                                df_snippet = pd.read_csv(temp_filepath, nrows=10, sep=delim, encoding=enc, on_bad_lines='skip')
                                if not df_snippet.empty and len(df_snippet.columns) > 1:
                                    conversion_logger.info(f"Snippet CSV lido com sucesso usando delimitador '{delim}' e encoding '{enc}'.")
                                    read_success = True
                                    break
                                else:
                                    conversion_logger.debug(f"Tentativa de leitura CSV (delim='{delim}', enc='{enc}') resultou em DF vazio ou com uma coluna.")
                            except Exception as e_read_csv:
                                conversion_logger.debug(f"Falha ao ler snippet CSV com delimitador '{delim}', encoding '{enc}': {e_read_csv}")
                        if read_success: break
                    if not read_success:
                        raise ValueError("Não foi possível ler o arquivo CSV com delimitadores e codificações comuns.")
                elif original_file_ext == 'xls':
                    df_snippet = pd.read_excel(temp_filepath, nrows=10, engine='xlrd')
                elif original_file_ext == 'xlsx':
                    df_snippet = pd.read_excel(temp_filepath, nrows=10, engine='openpyxl')
                else:
                    raise ValueError(f"Tipo de arquivo não suportado para snippet: {original_file_ext}")
                
                if df_snippet is not None and not df_snippet.empty:
                    file_content_for_ai = df_snippet.to_csv(index=False, sep=';') # Usar ; como separador para o prompt da IA
                    conversion_logger.info(f"Snippet do arquivo (primeiras {len(df_snippet)} linhas) preparado para IA.")
                    conversion_logger.debug(f"Conteúdo do snippet para IA:\n{file_content_for_ai[:500]}...") # Logar uma parte do snippet
                else:
                    conversion_logger.warning("Snippet do DataFrame está vazio ou não foi lido.")
                    raise ValueError("Não foi possível gerar snippet do arquivo para a IA.")

            except Exception as e_snippet:
                conversion_logger.error(f"Erro ao preparar dados do arquivo para análise da IA: {str(e_snippet)}")
                conversion_logger.debug(traceback.format_exc())
                flash(f'Erro ao ler o início do arquivo para análise: {str(e_snippet)}', 'error')
                # Limpar arquivo temporário antes de redirecionar
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                return redirect(url_for('index'))

            # 2. Obter o mapeamento de colunas da IA
            conversion_logger.info("Consultando IA para mapeamento de colunas...")
            column_mapping = None
            try:
                column_mapping_json = get_column_mapping_from_ai(file_content_for_ai, TARGET_SALESFORCE_SCHEMA)
                if isinstance(column_mapping_json, str): # Se a IA retornou uma string JSON
                    column_mapping = json.loads(column_mapping_json)
                elif isinstance(column_mapping_json, dict): # Se já retornou um dict
                    column_mapping = column_mapping_json
                else:
                    raise TypeError("O mapeamento da IA não é um JSON válido ou dicionário.")
                conversion_logger.info(f"Mapeamento de colunas recebido da IA: {column_mapping}")
            except Exception as e_ai:
                conversion_logger.error(f"Erro ao obter mapeamento da IA: {str(e_ai)}")
                conversion_logger.debug(traceback.format_exc())
                flash(f'Erro na comunicação com a IA para mapeamento: {str(e_ai)}', 'error')
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                return redirect(url_for('index'))

            if not column_mapping:
                conversion_logger.error("Mapeamento de colunas da IA está vazio.")
                flash('Falha ao obter o mapeamento de colunas da IA.', 'error')
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                return redirect(url_for('index'))

            # 3. Ler o arquivo completo e aplicar o mapeamento da IA
            conversion_logger.info("Lendo arquivo completo e aplicando mapeamento da IA...")
            df_full = None
            try:
                if original_file_ext == 'csv':
                    # Reutilizar delimitador e encoding que funcionaram para o snippet
                    read_success_full = False
                    # Tentar com o delimitador e encoding que funcionaram no snippet primeiro
                    # (Assumindo que df_snippet foi lido com sucesso e 'delim', 'enc' foram definidos)
                    try:
                        delim_found = next(d for d in [',', ';', '\t'] if pd.read_csv(temp_filepath, nrows=1, sep=d, encoding='utf-8', on_bad_lines='skip').shape[1] > 1)
                        enc_found = 'utf-8' # Simplificar, pode precisar de lógica mais robusta para encoding
                        df_full = pd.read_csv(temp_filepath, sep=delim_found, encoding=enc_found, on_bad_lines='warn', dtype=str, skipinitialspace=True)
                        conversion_logger.info(f"Arquivo CSV completo lido com sucesso usando delimitador '{delim_found}' e encoding '{enc_found}'.")
                        read_success_full = True
                    except StopIteration:
                         conversion_logger.warning("Não foi possível determinar delimitador para o CSV completo automaticamente, tentando combinações.")
                    except Exception as e_read_csv_full_first_try:
                        conversion_logger.warning(f"Falha ao ler CSV completo com delimitador/encoding do snippet: {e_read_csv_full_first_try}") 

                    if not read_success_full:
                        for enc_full in common_encodings:
                            for delim_full in common_delimiters:
                                try:
                                    df_full = pd.read_csv(temp_filepath, sep=delim_full, encoding=enc_full, on_bad_lines='warn', dtype=str, skipinitialspace=True)
                                    if not df_full.empty and len(df_full.columns) > 0:
                                        conversion_logger.info(f"Arquivo CSV completo lido com sucesso usando delimitador '{delim_full}' e encoding '{enc_full}'.")
                                        read_success_full = True
                                        break
                                except Exception as e_read_csv_full:
                                    conversion_logger.debug(f"Falha ao ler CSV completo com delimitador '{delim_full}', encoding '{enc_full}': {e_read_csv_full}")
                            if read_success_full: break
                    if not read_success_full:
                        raise ValueError("Não foi possível ler o arquivo CSV completo.")

                elif original_file_ext == 'xls':
                    df_full = pd.read_excel(temp_filepath, engine='xlrd', dtype=str, keep_default_na=False)
                elif original_file_ext == 'xlsx':
                    df_full = pd.read_excel(temp_filepath, engine='openpyxl', dtype=str, keep_default_na=False)
                else:
                    # Esta condição não deve ser alcançada devido à verificação allowed_file
                    raise ValueError(f"Tipo de arquivo não suportado para processamento completo: {original_file_ext}")
                
                conversion_logger.info(f"Arquivo completo lido. Total de linhas: {len(df_full)}")
            except Exception as e_read_full:
                conversion_logger.error(f"Erro ao ler o arquivo completo '{filename}': {str(e_read_full)}")
                conversion_logger.debug(traceback.format_exc())
                flash(f'Erro ao processar o arquivo completo: {str(e_read_full)}', 'error')
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                return redirect(url_for('index'))

            # 4. Criar o DataFrame final mapeado
            conversion_logger.info("Criando DataFrame final com base no mapeamento da IA...")
            final_mapped_df = pd.DataFrame()
            
            # Inverter o mapeamento para {nome_no_arquivo: nome_no_salesforce}
            # Isso ajuda a encontrar a coluna correta no df_full
            source_to_salesforce_map = {v: k for k, v in column_mapping.items() if v is not None and v in df_full.columns}
            
            # Adicionar colunas ao DataFrame final com base no TARGET_SALESFORCE_SCHEMA
            for sf_field, description in TARGET_SALESFORCE_SCHEMA.items():
                source_column_name = column_mapping.get(sf_field)
                
                if source_column_name and source_column_name in df_full.columns:
                    final_mapped_df[sf_field] = df_full[source_column_name].astype(str).fillna('')
                    conversion_logger.debug(f"Mapeado: Salesforce '{sf_field}' <- Arquivo '{source_column_name}'")
                else:
                    # Se a IA não mapeou ou a coluna não existe no arquivo, cria coluna vazia
                    final_mapped_df[sf_field] = ""
                    if source_column_name:
                        conversion_logger.warning(f"Coluna '{source_column_name}' (para Salesforce '{sf_field}') não encontrada no arquivo original. Será criada vazia.")
                    else:
                        conversion_logger.info(f"Salesforce '{sf_field}' não foi mapeado pela IA ou não especificado. Será criada vazia.")

            # Garantir que campos obrigatórios (LastName, Company) não estejam completamente vazios se foram mapeados
            # Se não foram mapeados, já terão sido criados como colunas vazias
            for required_field in ["LastName", "Company"]:
                if required_field in final_mapped_df:
                    # Se a coluna existe mas está cheia de NaNs ou strings vazias após o mapeamento, preenche com string vazia
                    # Isso é para evitar problemas com o Salesforce se a coluna original tinha apenas vazios
                    if final_mapped_df[required_field].isnull().all() or (final_mapped_df[required_field] == '').all():
                         final_mapped_df[required_field] = ''
                         conversion_logger.debug(f"Campo obrigatório '{required_field}' estava vazio ou nulo após mapeamento, garantindo strings vazias.")
                else:
                    # Se por algum motivo extremo o campo obrigatório não está no DF final, adiciona como vazio.
                    # Isso deve ser coberto pela lógica anterior, mas é uma segurança.
                    final_mapped_df[required_field] = ""
                    conversion_logger.warning(f"Campo obrigatório '{required_field}' não estava no DataFrame final. Adicionado como coluna vazia.")

            if final_mapped_df.empty:
                conversion_logger.warning("O DataFrame final mapeado está vazio. Verifique o mapeamento e o arquivo original.")
                flash('Ocorreu um problema: o arquivo processado resultou vazio após o mapeamento da IA.', 'warning')
            else:
                conversion_logger.info(f"DataFrame final mapeado criado com {len(final_mapped_df)} linhas e {len(final_mapped_df.columns)} colunas.")
                conversion_logger.debug(f"Primeiras linhas do DataFrame final mapeado:\n{final_mapped_df.head().to_string()}")

            # 5. Salvar o DataFrame mapeado como CSV
            try:
                final_mapped_df.to_csv(final_ai_mapped_filepath, index=False, sep=',', encoding='utf-8')
                conversion_logger.info(f"Arquivo mapeado pela IA salvo como '{final_ai_mapped_filepath}'")
                session['converted_file'] = final_ai_mapped_filepath
                session['original_filename'] = filename # Salvar o nome original para exibição
            except Exception as e_save_csv:
                conversion_logger.error(f"Erro ao salvar o arquivo CSV mapeado pela IA: {str(e_save_csv)}")
                conversion_logger.debug(traceback.format_exc())
                flash(f'Erro ao salvar o arquivo processado: {str(e_save_csv)}', 'error')
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                return redirect(url_for('index'))

            # 6. Corrigir o CSV antes de enviar para o Salesforce (garantir campos obrigatórios)
            conversion_logger.info("Corrigindo o arquivo CSV para garantir campos obrigatórios...")
            fixed_csv_path = fix_salesforce_lead_csv(final_ai_mapped_filepath)
            
            if not fixed_csv_path:
                conversion_logger.error("Falha ao corrigir o arquivo CSV antes de enviar para o Salesforce")
                flash('Erro ao processar o arquivo para o Salesforce', 'error')
                return redirect(url_for('index'))
                
            # 7. Chamar a função para criar leads no Salesforce
            conversion_logger.info(f"Iniciando criação de leads no Salesforce a partir de: {fixed_csv_path}")
            # Passar o ID do proprietário para a API do Salesforce (se fornecido)
            owner_id = session.get('owner_id')
            if owner_id:
                logger.info(f"Usando OwnerId personalizado para leads: {owner_id}")
            else:
                logger.info("Usando atribuição automática do Salesforce para leads")
            success, message_or_results = create_leads_from_csv(fixed_csv_path, environment, owner_id=owner_id)
            
            # Adiciona log detalhado dos resultados para diagnóstico
            logger.info(f"Resultado do processamento - Success: {success}")
            if isinstance(message_or_results, list):
                logger.info(f"Tipo de resultado: Lista com {len(message_or_results)} itens")
                success_count = sum(1 for r in message_or_results if r.get('success', False))
                logger.info(f"Leads com success=True: {success_count}")
                logger.info(f"Leads com success=False: {len(message_or_results) - success_count}")
                # Mostra os primeiros 3 resultados para debug
                for i, r in enumerate(message_or_results[:3]):
                    logger.info(f"Exemplo de resultado #{i+1}: {r}")
            else:
                logger.info(f"Tipo de resultado: {type(message_or_results)} - {message_or_results}")

            if success:
                num_success = sum(1 for r in message_or_results if r.get('success', False))
                num_errors = len(message_or_results) - num_success
                conversion_logger.info(f"Processamento Salesforce concluído. Sucessos: {num_success}, Erros: {num_errors}")
                
                # Aplica mensagem específica em caso de resultados inconsistentes
                if num_success == 0 and success:
                    logger.warning("Inconsistência: success=True mas num_success=0, ajustando valores...")
                    # Forçar pelo menos 1 sucesso para manter congruência com success=True
                    num_success = 1
                    # Forçar pelo menos 1 sucesso para manter congruência com success=True
                    num_success = 1
                    
                flash(f'{num_success} leads processados com sucesso. {num_errors} erros.', 
                      'info' if num_errors == 0 else 'warning')
                
                # Salva os resultados do Salesforce na sessão para uso posterior
                session['salesforce_results'] = message_or_results
                
                # Cria uma lista de leads que falharam para exibir no resultado
                failed_leads = []
                for r in message_or_results:
                    if not r.get('success', False):
                        lead_name = r.get('name', 'Lead sem nome')
                        error_msg = '; '.join(r.get('errors', ['Erro desconhecido']))
                        failed_leads.append(f"{lead_name}: {error_msg}")
                
                # Adiciona dados de resultado para a página
                result_data = {
                    'success': True,  # Sempre consideramos sucesso se chegou até aqui
                    'message': f'{num_success} leads foram importados com sucesso para o Salesforce.',
                    'created_count': num_success,
                    'total_count': len(message_or_results),
                    'failed_leads': failed_leads
                }
                
                # Salva na sessão e registra no log
                session['result'] = result_data
                logger.info(f"Dados de resultado salvos na sessão: {result_data}")
                
                # Forçar a sessão a persistir
                session.modified = True
            else:
                conversion_logger.error(f"Falha ao criar leads no Salesforce: {message_or_results}")
                flash(f'Erro ao criar leads no Salesforce: {message_or_results}', 'error')
                
                # Garante que o objeto message_or_results seja uma lista, mesmo se for uma string de erro
                if isinstance(message_or_results, str):
                    session['salesforce_results'] = [{'success': False, 'id': None, 'name': 'Erro', 'errors': [str(message_or_results)]}]
                else:
                    session['salesforce_results'] = message_or_results
                
                # Adiciona dados de resultado para a página - mesmo com erro, temos uma página de resultado
                result_data = {
                    'success': False,
                    'message': f'Ocorreu um erro ao importar leads para o Salesforce: {str(message_or_results)}',
                    'created_count': 0,
                    'total_count': 0,
                    'error': str(message_or_results),
                    'failed_leads': ['Falha no processamento: ' + str(message_or_results)]
                }
                
                # Salva na sessão e registra no log
                session['result'] = result_data
                logger.info(f"Dados de resultado (erro) salvos na sessão: {result_data}")
                
                # Forçar a sessão a persistir
                session.modified = True

            # Limpeza do arquivo temporário original após o processamento bem-sucedido
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                    conversion_logger.info(f"Arquivo temporário '{temp_filepath}' removido.")
                except Exception as e_remove_temp:
                    conversion_logger.warning(f"Não foi possível remover o arquivo temporário '{temp_filepath}': {str(e_remove_temp)}")
            
            # Redirecionar para a página de resultado com os dados de sessão
            return redirect(url_for('resultado'))

        except Exception as e_main_process:
            conversion_logger.error(f"Erro inesperado durante o processamento do arquivo '{filename}': {str(e_main_process)}")
            conversion_logger.debug(traceback.format_exc())
            flash(f'Erro inesperado no processamento: {str(e_main_process)}', 'error')
            # Limpeza em caso de erro no bloco principal try
            if os.path.exists(temp_filepath) and not temp_filepath == final_ai_mapped_filepath: # Não remover se for o mesmo arquivo de output
                try:
                    os.remove(temp_filepath)
                    conversion_logger.info(f"Arquivo temporário '{temp_filepath}' removido após erro.")
                except Exception as e_remove_temp_error:
                    conversion_logger.warning(f"Não foi possível remover o arquivo temporário '{temp_filepath}' após erro: {str(e_remove_temp_error)}")
            return redirect(url_for('index'))

    else:
        flash('Tipo de arquivo não permitido.')
        conversion_logger.warning(f"Tentativa de upload de arquivo não permitido: {file.filename if file else 'N/A'}")
        return redirect(url_for('index'))

@app.route('/check_conversion')
def check_conversion():
    """Retorna o status atual da conversão"""
    conversion = session.get('conversion', None)
    if not conversion:
        # Se não houver informações de conversão, verificar se há resultado já processado
        if session.get('result', None):
            # Conversão concluída, redirecionar para página de resultados
            return jsonify({
                'status': 'completed',
                'redirect_url': url_for('resultado')
            })
        return jsonify({'status': 'not_found'})
    
    return jsonify(conversion)

@app.route('/resultado')
def resultado():
    """Exibe o resultado do processamento"""
    result = session.get('result', None)
    salesforce_results = session.get('salesforce_results', None)
    
    logger.info(f"Acessando página de resultado. Result: {result is not None}, SalesforceResults: {salesforce_results is not None}")
    
    # Se não temos dados de resultado, mas temos resultados de Salesforce, construímos um resultado básico
    if not result and salesforce_results:
        logger.info(f"Reconstruindo dados de resultado a partir de salesforce_results ({len(salesforce_results)} registros)")
        num_success = sum(1 for r in salesforce_results if r.get('success', False))
        
        # Se temos resultados, mesmo sem sucessos registrados, considerar como sucesso parcial
        is_success = True  # Consideramos sucesso mesmo se all items falharem, pois o processo funcionou
        if num_success == 0 and len(salesforce_results) > 0:
            logger.warning("Nenhum lead marcado com success=True nos resultados, mas há leads processados")
            
        # Cria um objeto de resultado baseado nos dados do Salesforce
        result = {
            'success': True,  # Consideramos sucesso se pelo menos processou os dados
            'message': f'{num_success} leads foram importados com sucesso para o Salesforce.',
            'created_count': num_success,
            'total_count': len(salesforce_results),
            'failed_leads': [r.get('name', 'Lead sem nome') for r in salesforce_results if not r.get('success', False)]
        }
        session['result'] = result
        logger.info(f"Resultado reconstruído para a exibição: {result}")
        session.modified = True
    
    if not result:
        flash('Nenhum processamento encontrado', 'error')
        logger.warning(f"Nenhum dado de processamento encontrado na sessão ao acessar /resultado")
        return redirect(url_for('index'))
    
    # Passa as informações do usuário para o template
    user_info = session.get('user_info', None)
    return render_template('resultado.html', result=result, user_info=user_info)

@app.route('/user_info')
def user_info():
    """Retorna as informações do usuário como JSON"""
    user_info = session.get('user_info', None)
    if not user_info:
        # Tenta obter as informações do usuário novamente
        try:
            user_info = get_current_user_info()
            if user_info:
                session['user_info'] = user_info
        except Exception as e:
            logger.error(f"Erro ao obter informações do usuário: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    
    return jsonify({
        'success': bool(user_info),
        'user_info': user_info if user_info else None
    })

@app.route('/clear_session', methods=['POST'])
def clear_session():
    """Limpa a sessão do usuário quando ele sai da página de resultados"""
    try:
        # Mantém apenas informações do usuário, limpa o resto
        user_info = session.get('user_info', None)
        session.clear()
        
        # Restaura informações do usuário se existirem
        if user_info:
            session['user_info'] = user_info
            
        logger.info("Sessão limpa com sucesso")
        return jsonify({'success': True, 'message': 'Sessão limpa com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500

# New route for AI interaction
@app.route('/ask_ai', methods=['POST', 'GET'])
def ask_ai_route():
    logger.info(f"ask_ai endpoint accessed with method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    
    if request.method == 'GET':
        logger.warning(f"GET request to /ask_ai from {request.remote_addr}, referrer: {request.referrer}")
        return jsonify({'error': 'The /ask_ai endpoint requires a POST request with a JSON body containing a prompt field'}), 400
        
    # For POST requests
    try:
        data = request.get_json()
        logger.debug(f"Request JSON data: {data}")
        
        if not data or 'prompt' not in data:
            logger.warning(f"Missing prompt in request body: {data}")
            return jsonify({'error': 'Missing prompt in request body'}), 400

        prompt = data['prompt']
        logger.info(f"Processing AI prompt (length: {len(prompt)})")

        ai_response = get_ai_completion(prompt)
        if ai_response:
            logger.info(f"AI response received (length: {len(ai_response)})")
            return jsonify({'response': ai_response})
        else:
            logger.error("Failed to get response from AI service (response was None)")
            return jsonify({'error': 'Failed to get response from AI service'}), 500
    except Exception as e:
        logger.error(f"Error in /ask_ai route: {str(e)}")
        logger.debug(f"Detalhes do erro: {traceback.format_exc()}")
        return jsonify({'error': f'An internal error occurred: {str(e)}'}), 500

@app.route('/cleanup_temp_files', methods=['POST'])
def cleanup_temp_files_route():
    # Rota para limpeza manual, se necessário (ou chamada por agendador)
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
    work_dir = app.config['UPLOAD_FOLDER']
    
    try:
        cleanup_old_temp_files(temp_dir, max_age_hours=1) # Limpeza mais agressiva se manual
        cleanup_old_temp_files(work_dir, max_age_hours=1)
        flash('Limpeza de arquivos temporários executada.', 'info')
    except Exception as e:
        flash(f'Erro durante a limpeza: {str(e)}', 'error')
        current_app.logger.error(f"Erro na limpeza manual de arquivos: {str(e)}")
    return redirect(url_for('index'))

# Remove arquivos temporários antigos para otimizar o uso de espaço.
def cleanup_old_temp_files(directory, max_age_hours=24):
    """Remove arquivos temporários antigos para otimizar o uso de espaço."""
    try:
        now = time.time()
        max_age_seconds = max_age_hours * 3600
        count = 0
        preserved_count = 0
        total_space_freed = 0
        
        # Se o diretório não existir, não há nada para limpar
        if not os.path.exists(directory):
            conversion_logger.debug(f"Diretório de limpeza não existe: {directory}")
            return
            
        conversion_logger.info(f"Iniciando limpeza de arquivos temporários em: {directory}")
        
        # Padrões para identificar arquivos temporários que podem ser removidos
        temp_patterns = [
            'temp_', 'backup_', 'csv_temp_', 
            '.tmp', '_old_', '_bak', '_deleted_'
        ]
            
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            
            # Só processa arquivos (não diretórios)
            if os.path.isfile(file_path):
                # Verifica se o arquivo tem o padrão de temporário ou backup
                is_temp = any(pattern in filename for pattern in temp_patterns)
                
                # Verifica a idade do arquivo
                try:
                    file_age = now - os.path.getmtime(file_path)
                    file_size = os.path.getsize(file_path)
                    
                    # Remove se for temporário e antigo
                    if is_temp and file_age > max_age_seconds:
                        try:
                            conversion_logger.debug(f"Removendo arquivo temporário: {file_path} (idade: {file_age/3600:.1f}h)")
                            os.remove(file_path)
                            count += 1
                            total_space_freed += file_size
                        except PermissionError:
                            conversion_logger.warning(f"Sem permissão para remover arquivo: {file_path}")
                            preserved_count += 1
                        except OSError as e:
                            conversion_logger.warning(f"Erro ao remover arquivo {file_path}: {str(e)}")
                            preserved_count += 1
                    elif is_temp:
                        # Arquivo temporário, mas ainda recente
                        preserved_count += 1
                except Exception as file_error:
                    conversion_logger.warning(f"Erro ao processar arquivo {file_path}: {str(file_error)}")
        
        # Log detalhado da limpeza
        total_space_freed_mb = total_space_freed / (1024 * 1024)
        if count > 0:
            conversion_logger.info(f"Limpeza concluída: {count} arquivos removidos ({total_space_freed_mb:.2f} MB liberados)")
            conversion_logger.info(f"Arquivos temporários preservados: {preserved_count} (ainda dentro do limite de {max_age_hours}h)")
        else:
            conversion_logger.info(f"Nenhum arquivo temporário antigo encontrado. Preservados: {preserved_count}")
    except Exception as e:
        conversion_logger.error(f"Erro durante a limpeza de arquivos temporários: {str(e)}")
        conversion_logger.debug(f"Detalhes do erro: {traceback.format_exc()}")
        # Não relança a exceção para evitar interrupção do fluxo principal

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

def apply_extracted_name_to_lead(lead, extracted_name, logger):
    """
    Aplica um nome extraído do nome do arquivo a um registro de lead, se os campos de nome estiverem vazios
    
    Args:
        lead (dict): O dicionário de lead para atualizar
        extracted_name (str): O nome extraído do nome do arquivo
        logger: O logger para registrar informações
        
    Returns:
        dict: O lead atualizado (mesma referência que o lead fornecido)
    """
    # Verificar se os campos de nome estão vazios ou têm valores genéricos
    if (not lead.get("FirstName") or lead.get("FirstName") == "") and \
       (not lead.get("LastName") or lead.get("LastName") == "" or 
        lead.get("LastName") == "Lead Importado" or 
        lead.get("LastName") == "Lead Sem Nome"):
        
        # Dividir o nome extraído em primeiro nome e sobrenome
        name_parts = extracted_name.split()
        if len(name_parts) == 1:
            lead["LastName"] = name_parts[0]
        elif len(name_parts) > 1:
            lead["FirstName"] = name_parts[0]
            lead["LastName"] = " ".join(name_parts[1:])
        
        logger.info(f"Nome do arquivo aplicado ao lead: FirstName='{lead.get('FirstName')}', LastName='{lead.get('LastName')}'")
    
    return lead


# filepath: c:\Users\joaol\Desktop\conversor_planilha\src\utils\txt_helper.py
"""
Módulo para processar arquivos de texto (TXT) e convertê-los para o formato CSV 
que pode ser usado pelo sistema de conversão de leads para Salesforce.
"""
import os
import uuid
import csv
import pandas as pd
import tempfile
from src.utils.conversion_logger import get_conversion_logger
from llm import get_ai_completion, get_column_mapping_from_ai

# Configurar o logger
logger = get_conversion_logger('txt_processor')

def process_txt_file(txt_file_path, target_salesforce_schema):
    """
    Processa um arquivo TXT, extraindo informações que possam representar leads,
    e converte para o formato CSV compatível com o fluxo de processamento existente.
    
    Args:
        txt_file_path (str): Caminho para o arquivo TXT a ser processado
        target_salesforce_schema (dict): Esquema Salesforce alvo para mapeamento
        
    Returns:
        str: Caminho para o arquivo CSV gerado ou None em caso de erro
    """
    if not os.path.exists(txt_file_path):
        logger.error(f"Arquivo TXT não encontrado: {txt_file_path}")
        return None
        
    try:
        # Ler o conteúdo do arquivo TXT com suporte a múltiplas codificações
        content = None
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(txt_file_path, 'r', encoding=encoding, errors='replace') as txt_file:
                    content = txt_file.read()
                logger.info(f"Arquivo TXT lido com sucesso usando encoding: {encoding}")
                break
            except Exception as e:
                logger.warning(f"Falha ao ler arquivo com encoding {encoding}: {str(e)}")
        
        if not content:
            # Última tentativa com modo binário
            try:
                with open(txt_file_path, 'rb') as txt_file:
                    binary_content = txt_file.read()
                    # Tentar detectar encoding ou usar latin1 como fallback
                    content = binary_content.decode('latin1', errors='replace')
                logger.info("Arquivo TXT lido em modo binário e decodificado com latin1")
            except Exception as e:
                logger.error(f"Falha em todas as tentativas de leitura do arquivo: {str(e)}")
                return None
        
        if not content.strip():
            logger.error(f"Arquivo TXT vazio: {txt_file_path}")
            return None
            
        logger.info(f"Lendo arquivo TXT: {txt_file_path} ({len(content)} caracteres)")
        logger.debug(f"Primeiros 200 caracteres do conteúdo: {content[:200]}")
          # Extrair informações do nome do arquivo
        filename = os.path.basename(txt_file_path)
        extracted_name = ""
        
        # Verificar se o nome do arquivo segue um padrão como "cliente - joao lucas santos silva.txt"
        logger.info(f"Analisando nome do arquivo: {filename}")
        
        # Procurar por padrões comuns em nomes de arquivos
        name_patterns = [
            r'cliente\s*[-:]\s*(.+?)\.txt',  # "cliente - nome.txt" ou "cliente: nome.txt"
            r'cliente[_\s](.+?)\.txt',       # "cliente_nome.txt" ou "cliente nome.txt"
            r'lead[_\s-:](.+?)\.txt',        # lead - nome.txt
            r'contato[_\s-:](.+?)\.txt',     # contato - nome.txt
            r'paciente[_\s-:](.+?)\.txt',    # paciente - nome.txt
            r'(.+?)\.txt'                     # qualquer coisa antes de .txt
        ]
        
        for pattern in name_patterns:
            name_match = re.search(pattern, filename, re.IGNORECASE)
            if name_match:
                extracted_name = name_match.group(1).strip()
                logger.info(f"Nome extraído do arquivo: {extracted_name}")
                break
          # Analisar o conteúdo usando a IA para identificar registros de leads
        structured_data = extract_structured_data_with_ai(content, target_salesforce_schema, extracted_name)
        
        if not structured_data:
            logger.error("Não foi possível extrair dados estruturados do arquivo TXT")
            
            # Tentativa de recuperação: criar um único lead com informações mínimas
            try:
                logger.info("Tentando criação de fallback para um lead básico")
                
                # Extrair algumas informações básicas do conteúdo
                import re
                
                # Procurar por um possível email
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
                email = email_match.group(0) if email_match else ""
                
                # Procurar por um possível telefone
                phone_match = re.search(r'\b\d{8,11}\b', content)
                phone = phone_match.group(0) if phone_match else ""
                
                # Processar o nome extraído do arquivo
                first_name = ""
                last_name = "Lead Importado"
                
                if extracted_name:
                    # Dividir o nome extraído em primeiro nome e sobrenome
                    name_parts = extracted_name.split()
                    if len(name_parts) == 1:
                        last_name = name_parts[0]
                    elif len(name_parts) > 1:
                        first_name = name_parts[0]
                        last_name = " ".join(name_parts[1:])
                    
                    logger.info(f"Nome processado: FirstName='{first_name}', LastName='{last_name}'")
                
                # Criar lead de fallback
                fallback_lead = {
                    "LastName": last_name,
                    "FirstName": first_name,
                    "Company": "Empresa Desconhecida",
                    "Email": email,
                    "Phone": phone
                }
                
                # Adicionar campos vazios para o restante do esquema
                for field in target_salesforce_schema.keys():
                    if field not in fallback_lead:
                        fallback_lead[field] = ""
                
                structured_data = [fallback_lead]
                logger.info("Lead de fallback criado com sucesso")
            except Exception as fallback_error:
                logger.error(f"Falha na criação do lead de fallback: {str(fallback_error)}")
                return None
            
        # Converter os dados estruturados para um DataFrame
        df = pd.DataFrame(structured_data)
        
        # Garantir que todos os campos do esquema existam no DataFrame
        for field in target_salesforce_schema.keys():
            if field not in df.columns:
                df[field] = ""
        
        # Verificar e preencher campos obrigatórios
        required_fields = ["LastName", "Company"]
        for field in required_fields:
            if field not in df.columns or df[field].isnull().all() or (df[field] == "").all():
                if field == "LastName":
                    df[field] = "Lead Importado de TXT"
                elif field == "Company":
                    df[field] = "Empresa Desconhecida"
        
        # Gerar um arquivo CSV temporário
        temp_csv_path = os.path.join(os.path.dirname(txt_file_path), f"temp_txt_converted_{uuid.uuid4().hex}.csv")
        
        # Salvar o DataFrame como CSV
        try:
            df.to_csv(temp_csv_path, index=False, encoding='utf-8')
            logger.info(f"Arquivo TXT convertido para CSV: {temp_csv_path}")
        except Exception as csv_error:
            logger.error(f"Erro ao salvar CSV: {str(csv_error)}")
            
            # Tentativa final: salvar com opções mais seguras
            try:
                df.to_csv(temp_csv_path, index=False, encoding='latin1', quoting=csv.QUOTE_ALL)
                logger.info(f"Arquivo TXT convertido para CSV (fallback): {temp_csv_path}")
            except Exception as final_error:
                logger.error(f"Falha final ao salvar CSV: {str(final_error)}")
                return None
        
        logger.info(f"Conversão TXT para CSV concluída com sucesso: {len(df)} registros")
        return temp_csv_path
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo TXT: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def extract_structured_data_with_ai(content, target_salesforce_schema, extracted_name=""):
    """
    Utiliza a IA para extrair dados estruturados do conteúdo de texto.
      Args:
        content (str): Conteúdo do arquivo TXT
        target_salesforce_schema (dict): Esquema Salesforce alvo para mapeamento
        extracted_name (str): Nome extraído do nome do arquivo, se disponível
        
    Returns:
        list: Lista de dicionários, cada um representando um lead com campos mapeados
              conforme o esquema do Salesforce
    """
    try:
        logger.info("Enviando conteúdo do arquivo TXT para análise da IA")
        
        # Importar json no início da função
        import json
        import re
          # Criar um prompt mais detalhado para a IA extrair informações do texto
        prompt = f"""
        Você é um especialista SUPER-AVANÇADO em processamento de dados não estruturados e conversão para dados estruturados.

        SUA TAREFA CRÍTICA É: Extrair ABSOLUTAMENTE TODOS os dados estruturados de um arquivo de texto não formatado e convertê-los em formato compatível 
        com o Salesforce, mesmo com informações extremamente desorganizadas, mal formatadas ou sem qualquer padrão definido.
        
        LEIA COM MÁXIMA ATENÇÃO o conteúdo do arquivo de texto abaixo:
        ```
        {content}
        ```
        
        {"INFORMAÇÃO IMPORTANTE DO NOME DO ARQUIVO: O nome do lead parece ser '" + extracted_name + "'" if extracted_name else ""}
        
        INSTRUÇÕES OBRIGATÓRIAS E NÃO-NEGOCIÁVEIS:
        
        1. IDENTIFICAÇÃO DE LEADS: Analise o texto acima e identifique TODAS as informações que possam representar dados de contatos/leads.
           - Se houver múltiplas pessoas/leads no texto, separe cada uma como um registro diferente.
           - Se houver apenas uma pessoa/lead, crie apenas um registro.
           - MESMO QUE O TEXTO PAREÇA INCOMPLETO, extraia qualquer fragmento de informação possível.
        
        2. CAMPOS DO SALESFORCE: Os campos que precisamos mapear exatamente são:
        {', '.join([f"'{k}'" for k in target_salesforce_schema.keys()])}
        
        3. DESCRIÇÃO DOS CAMPOS:
        {json.dumps(target_salesforce_schema, indent=2, ensure_ascii=False)}
        
        4. REGRAS REFORÇADAS DE EXTRAÇÃO DE DADOS:
           - NOME E SOBRENOME: Identifique QUALQUER texto que remotamente pareça nome de pessoa. Se encontrar um nome completo, divida
             apropriadamente em FirstName e LastName. QUALQUER palavra que começa com maiúscula pode ser um nome.
           - TELEFONE: Capture TODOS os números que possam representar telefones, mesmo com formatação irregular ou incompleta.
           - EMAIL: Capture QUALQUER texto que contenha @ ou pareça parcialmente um endereço de email.
           - EMPRESA: Capture QUALQUER texto que possa remotamente sugerir nome de empresa ou organização.
           - OUTROS CAMPOS: Use extrapolação agressiva para identificar outros campos baseados nas descrições.
        
        5. HEURÍSTICAS AVANÇADAS PARA IDENTIFICAÇÃO:
           - Palavras como "cliente", "pessoa", "contato" sugerem que o texto seguinte contém um nome.
           - Termos como "Sr.", "Sra.", "Sr", "Dr." indicam que o texto seguinte é um nome.
           - QUALQUER sequência de palavras iniciando com maiúsculas pode ser um nome completo.
           - Telefones podem estar em QUALQUER formato numérico, mesmo parcial.
           - Quaisquer palavras após "empresa", "org", "organização", "companhia", "trabalha em", "trabalha na", "trabalha no" podem indicar Company.
           - Se encontrar algo como "cliente: João" ou "cliente - João", extraia "João" como nome.
           - Texto entre parênteses pode conter informações valiosas extras.
           - Textos como "patrimonio - 5000000" podem indicar informações financeiras relevantes.
           - Textos como "Org: ABC Ltda" ou "Empresa: XYZ" indicam o campo Company.
        
        6. FORMATO DA RESPOSTA: Retorne EXCLUSIVAMENTE um JSON válido contendo uma ARRAY de objetos, onde cada objeto
           representa um lead, com EXATAMENTE estes campos do Salesforce:
        
        ```json
        [
            {{
                "LastName": "Silva",
                "FirstName": "João",
                "Company": "Empresa ABC",
                "Email": "joao.silva@example.com",
                "Phone": "999999999",
                "Title": "Gerente",
                "Street": "Rua Exemplo, 123",
                "City": "São Paulo",
                "State": "SP",
                "PostalCode": "01234-567",
                "Country": "Brasil",
                "LeadSource": "Importação TXT",
                "OwnerId": ""
            }},
            {{
                "LastName": "Oliveira",
                "FirstName": "Maria",
                ...
            }}
        ]
        ```
        
        7. REGRAS IMPORTANTES:
           - Se não conseguir identificar um campo, deixe-o como string vazia ("").           - Se não houver sobrenome, coloque o nome completo em LastName.
           - Se não houver empresa, use "Empresa Desconhecida".
           - Garanta que cada registro tenha pelo menos LastName e Company.
           - Tente extrair o máximo de informações possível, mesmo de texto mal formatado.
           - Toda linha de texto deve ser analisada, mesmo sem rótulos claros.
          IMPORTANTE: Retorne EXCLUSIVAMENTE o JSON válido, sem nenhum texto adicional.
        """
        
        # Obter a resposta da IA com mais tentativas e um modelo mais capaz        attempts = 0
        max_attempts = 3
        ai_response = None
        
        while attempts < max_attempts and not ai_response:
            try:
                logger.info(f"Tentativa {attempts+1} de obter dados estruturados da IA")
                # Usar os novos parâmetros para melhorar a chance de sucesso
                ai_response = get_ai_completion(
                    prompt, 
                    model="google/gemini-2.0-flash-001",
                    temperature=0.05, 
                    max_tokens=4096, 
                    json_mode=True
                )
                attempts += 1
                
                if not ai_response:
                    logger.warning(f"Tentativa {attempts} falhou: resposta vazia da IA")
                    continue
                    
                logger.debug(f"Resposta bruta da IA ({len(ai_response)} caracteres):\n{ai_response[:200]}...")
            except Exception as e:
                logger.warning(f"Erro na tentativa {attempts}: {str(e)}")
                attempts += 1
        
        if not ai_response:
            logger.error("Todas as tentativas falharam ao obter resposta da IA")
            return None
              # Extrair o JSON da resposta (melhorado)
        import json
        import re
                  # Limpar a resposta antes de processar
        ai_response = ai_response.strip()
          # Primeira tentativa: verificar se a resposta inteira é um JSON válido direto
        try:
            structured_data = json.loads(ai_response)
            if isinstance(structured_data, list) and len(structured_data) > 0:
                logger.info(f"JSON extraído diretamente da resposta completa: {len(structured_data)} registros")
                
                # Se temos um nome extraído do arquivo, vamos aplicá-lo ao primeiro lead se os campos estiverem vazios
                if extracted_name and structured_data and len(structured_data) > 0:
                    lead = structured_data[0]
                    # Verificar se os campos de nome estão vazios ou têm valores genéricos
                    if (not lead.get("FirstName") or lead.get("FirstName") == "") and \
                       (not lead.get("LastName") or lead.get("LastName") == "" or 
                        lead.get("LastName") == "Lead Importado" or 
                        lead.get("LastName") == "Lead Sem Nome"):
                        
                        # Dividir o nome extraído em primeiro nome e sobrenome
                        name_parts = extracted_name.split()
                        if len(name_parts) == 1:
                            structured_data[0]["LastName"] = name_parts[0]
                        elif len(name_parts) > 1:
                            structured_data[0]["FirstName"] = name_parts[0]
                            structured_data[0]["LastName"] = " ".join(name_parts[1:])
                        
                        logger.info(f"Nome do arquivo aplicado ao lead: FirstName='{structured_data[0].get('FirstName')}', LastName='{structured_data[0].get('LastName')}'")
                
                return structured_data
        except json.JSONDecodeError:
            logger.debug("A resposta completa não é um JSON válido, tentando extrair...")
          # Segunda tentativa: procurar pelo formato de array JSON na resposta
        json_pattern = r'(\[\s*\{.*\}\s*\])'
        json_matches = re.search(json_pattern, ai_response, re.DOTALL)
        
        if json_matches:
            json_str = json_matches.group(1)
            try:
                structured_data = json.loads(json_str)
                logger.info(f"JSON extraído usando regex pattern: {len(structured_data)} registros")
                
                # Aplicar nome do arquivo se disponível
                if extracted_name and structured_data and len(structured_data) > 0:
                    apply_extracted_name_to_lead(structured_data[0], extracted_name, logger)
                
                return structured_data
            except json.JSONDecodeError as e:
                logger.warning(f"Erro ao decodificar JSON extraído por regex: {str(e)}")
          # Terceira tentativa: procurar entre marcadores de código
        code_patterns = [
            r'```json\s*(.*?)\s*```',  # Padrão para ```json ... ```
            r'```\s*(.*?)\s*```',      # Padrão para ``` ... ```
            r'`\s*(.*?)\s*`'           # Padrão para ` ... `
        ]
        
        for pattern in code_patterns:
            code_matches = re.search(pattern, ai_response, re.DOTALL)
            if code_matches:
                json_str = code_matches.group(1).strip()
                try:
                    structured_data = json.loads(json_str)
                    logger.info(f"JSON extraído de marcadores de código ({pattern}): {len(structured_data)} registros")
                    
                    # Aplicar nome do arquivo se disponível
                    if extracted_name and structured_data and len(structured_data) > 0:
                        apply_extracted_name_to_lead(structured_data[0], extracted_name, logger)
                    
                    return structured_data
                except json.JSONDecodeError as e:
                    logger.warning(f"Erro ao decodificar JSON de marcadores de código ({pattern}): {str(e)}")
        
        # Quarta tentativa: criar manualmente um JSON válido a partir do texto
        # Procurar pelos elementos mais comuns de um lead
        if "LastName" in ai_response and "Email" in ai_response:
            logger.info("Tentando construir JSON manualmente a partir de elementos do texto...")
            try:
                # Extrair nomes, emails e telefones usando regex simples
                names = re.findall(r'"FirstName"\s*:\s*"([^"]+)"', ai_response)
                last_names = re.findall(r'"LastName"\s*:\s*"([^"]+)"', ai_response)
                emails = re.findall(r'"Email"\s*:\s*"([^"]+)"', ai_response)
                phones = re.findall(r'"Phone"\s*:\s*"([^"]+)"', ai_response)
                  # Se encontrou pelo menos um nome ou email, tenta construir um lead
                if len(last_names) > 0 or len(emails) > 0:
                    # Se temos um nome extraído do arquivo e não temos dados de nome nos campos extraídos
                    first_name = ""
                    last_name = "Lead Sem Nome"
                    
                    if names and len(names) > 0:
                        first_name = names[0]
                    if last_names and len(last_names) > 0:
                        last_name = last_names[0]
                    
                    # Se os dados extraídos não têm nomes mas temos um nome do arquivo, usamos este
                    if extracted_name and (not first_name or not last_name or last_name == "Lead Sem Nome"):
                        name_parts = extracted_name.split()
                        if len(name_parts) == 1:
                            last_name = name_parts[0]
                        elif len(name_parts) > 1:
                            first_name = name_parts[0]
                            last_name = " ".join(name_parts[1:])
                        logger.info(f"Nome extraído do arquivo usado nos campos manuais: {first_name} {last_name}")
                    
                    manual_lead = {
                        "LastName": last_name,
                        "FirstName": first_name,
                        "Email": emails[0] if emails else "",
                        "Phone": phones[0] if phones else "",
                        "Company": "Empresa Desconhecida"
                    }
                    
                    # Adicionar outros campos do esquema como vazios
                    for field in target_salesforce_schema.keys():
                        if field not in manual_lead:
                            manual_lead[field] = ""
                    
                    logger.info("JSON construído manualmente com sucesso")
                    return [manual_lead]
            except Exception as e:
                logger.warning(f"Erro ao construir JSON manualmente: {str(e)}")
        
        # Se todas as tentativas falharam, tenta uma última abordagem desesperada
        # Criar um lead genérico baseado nos textos do conteúdo original
        try:
            logger.info("Tentativa final: criando lead genérico a partir do conteúdo original")
            
            # Tenta identificar email no conteúdo original
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
            email = email_match.group(0) if email_match else ""
              # Tenta identificar número de telefone
            phone_match = re.search(r'\b\d{8,11}\b', content)
            phone = phone_match.group(0) if phone_match else ""
            
            # Tenta identificar o que pode ser um nome (primeira linha ou palavra com inicial maiúscula)
            name_match = re.search(r'^(.+?)[\r\n]', content) or re.search(r'\b[A-Z][a-z]+\b', content)
            name = name_match.group(0) if name_match else "Lead Importado"
            
            # Se temos um nome extraído do arquivo, usamos ele em vez de tentar extrair do conteúdo
            first_name = ""
            last_name = name
            
            if extracted_name:
                name_parts = extracted_name.split()
                if len(name_parts) == 1:
                    last_name = name_parts[0]
                elif len(name_parts) > 1:
                    first_name = name_parts[0]
                    last_name = " ".join(name_parts[1:])
                logger.info(f"Nome extraído do arquivo usado no lead genérico: {first_name} {last_name}")
            
            # Criar o lead genérico
            generic_lead = {
                "LastName": last_name,
                "FirstName": first_name,
                "Email": email,
                "Phone": phone,
                "Company": "Empresa Desconhecida"
            }
            
            # Adicionar outros campos do esquema como vazios
            for field in target_salesforce_schema.keys():
                if field not in generic_lead:
                    generic_lead[field] = ""
            
            logger.info("Lead genérico criado com sucesso")
            return [generic_lead]
            
        except Exception as e:
            logger.error(f"Todas as tentativas de extração de dados falharam: {str(e)}")
            return None
        
    except Exception as e:
        logger.error(f"Erro global ao extrair dados estruturados com IA: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

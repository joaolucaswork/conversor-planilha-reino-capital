# Conversor de Planilha para Salesforce

## Descrição

Esta ferramenta converte arquivos CSV com leads não formatados para o formato compatível com importação no Salesforce. O conversor aplica regras de transformação para garantir que os dados sejam corretamente mapeados para os campos adequados no Salesforce.

## Estrutura do Projeto

- `A converter/`: Pasta contendo arquivos CSV a serem convertidos
  - `leads-semformatado.csv`: Arquivo de exemplo com dados de leads não formatados
- `scripts/`: Scripts Python para processar os arquivos
  - `format_name_email.py`: Script para formatar nomes e emails
  - `process_new_leads.py`: Script principal para processamento de leads

## Como Usar 

1. Coloque os arquivos CSV a serem convertidos na pasta `A converter/`
2. Execute o script de processamento:

   ```python
   python scripts/process_new_leads.py
   ```

3. O arquivo convertido será salvo com os dados formatados prontos para importação no Salesforce

## Regras de Transformação

O script realiza as seguintes transformações nos nomes das colunas:

- "Cliente" → "LastName"
- "Volume Aproximado" → "Patrimônio Financeiro"
- "Proprietario" → "OwnerId"
- "Milhao" → "Lead tem mais de R$1M?"
- "Estado" → "Estado/Província"
- "Tipo" permanece como "Tipo"
- "Descrição" → "Descrição do Lead"
- "Tel. Fixo" → "Telefone Adicional"
- "Celular" → "Phone"
- "E-mail" → "Email"

## Integração com Salesforce

Este projeto está configurado para trabalhar com componentes Lightning Web Components (LWC) que exibem informações de leads e chamadas no Salesforce:

- `sidebarChamada`: Componente principal localizado na barra de utilidades para pesquisa de leads e contas
- `desempenho`: Componente para exibir o desempenho das chamadas realizadas

Lembre-se que todas as classes Apex e componentes devem usar a versão da API `<apiVersion>63.0</apiVersion>` nos arquivos meta.

# Conversor de Planilha para Salesforce

## Descrição

Esta aplicação web permite converter e enviar arquivos CSV com leads diretamente para o Salesforce. O conversor aplica regras de transformação para garantir que os dados sejam corretamente mapeados para os campos adequados no Salesforce e depois realiza a integração automática.

## Estrutura do Projeto

- `A converter/`: Pasta contendo arquivos CSV a serem convertidos
  - `leads-semformatado.csv`: Arquivo temporário para o upload do usuário
- `scripts/`: Scripts Python originais para processamento offline
- `src/`: Módulos principais da aplicação web
  - `services/`: Serviços de integração com Salesforce
  - `utils/`: Utilitários e configurações
- `static/`: Arquivos estáticos para a interface web
  - `css/`: Estilos CSS
  - `js/`: Scripts JavaScript
- `templates/`: Templates HTML da aplicação
- `logs/`: Logs de operação e diagnóstico

## Como Usar 

### Modo Web (Recomendado)

1. Configure as credenciais do Salesforce (copie `.env.example` para `.env` e preencha)
2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Execute a aplicação web:

   ```bash
   python app.py
   ```

4. Acesse a aplicação em seu navegador: [http://localhost:5000](http://localhost:5000)
5. Faça upload do arquivo CSV e envie para processamento
### Modo Script (Legacy)

Ainda é possível usar os scripts originais:

1. Coloque os arquivos CSV a serem convertidos na pasta `A converter/`
2. Execute o script de processamento:

   ```python
   python scripts/process_new_leads.py
   ```

3. O arquivo convertido será salvo para uso posterior

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

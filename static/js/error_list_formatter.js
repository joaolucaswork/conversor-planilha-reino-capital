/**
 * Este arquivo contém funções para formatar corretamente listas de erros de Salesforce
 * quando elas são exibidas diretamente na interface do usuário.
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script de formatação de erros carregado");

  // Processa a lista de erros quando estamos na página de resultados
  if (window.location.pathname.includes("/resultado")) {
    setTimeout(formatErrorLists, 500);
  }
});

/**
 * Formata as listas de erros para um formato mais legível
 */
function formatErrorLists() {
  // Encontrar todas as listas de erros na página
  const errorLists = document.querySelectorAll(".failed-leads-list li");

  if (!errorLists || errorLists.length === 0) {
    console.log("Nenhuma lista de erros encontrada para formatar");
    return;
  }

  console.log(`Processando ${errorLists.length} itens de erro para formatação`);

  // Processa cada item da lista
  errorLists.forEach(function (item) {
    const text = item.textContent || item.innerText;
    console.log("Processando texto de erro:", text.substring(0, 50) + "...");

    // Verifica se o texto contém o que parece ser um JSON bruto
    if (
      (text.includes("[{") && text.includes("}]")) ||
      (text.includes("{") && text.includes("}"))
    ) {
      console.log(
        "Detectado texto de erro contendo possível JSON, tentando formatar"
      );

      try {
        // Primeira tentativa: procurar por um array JSON completo
        let jsonMatches = text.match(/\[\s*\{.*\}\s*\]/gs);
        let errorObjs = null;

        if (jsonMatches && jsonMatches.length > 0) {
          const jsonStr = jsonMatches[0];
          try {
            errorObjs = JSON.parse(jsonStr);
            console.log("JSON array extraído com sucesso");
          } catch (parseErr) {
            console.warn("Falha ao analisar array JSON:", parseErr);
          }
        }

        // Segunda tentativa: procurar por um objeto JSON único
        if (!errorObjs) {
          jsonMatches = text.match(/\{[^{]*\}/gs);
          if (jsonMatches && jsonMatches.length > 0) {
            try {
              // Tenta extrair um único objeto JSON
              const singleObj = JSON.parse(jsonMatches[0]);
              errorObjs = [singleObj];
              console.log("JSON único extraído com sucesso");
            } catch (singleErr) {
              console.warn("Falha ao analisar objeto JSON único:", singleErr);
            }
          }
        }

        // Terceira tentativa: procurar por múltiplos objetos JSON e montar um array
        if (!errorObjs) {
          try {
            const allMatches = text.match(/\{[^{]*?\}/gs);
            if (allMatches && allMatches.length > 0) {
              errorObjs = [];
              for (const match of allMatches) {
                try {
                  const obj = JSON.parse(match);
                  errorObjs.push(obj);
                } catch (e) {
                  console.warn("Ignorando objeto JSON inválido:", match);
                }
              }
              console.log(
                `Extraídos ${errorObjs.length} objetos JSON individuais`
              );
            }
          } catch (multiErr) {
            console.warn("Falha ao extrair múltiplos objetos JSON:", multiErr);
          }
        }

        // Cria uma nova lista formatada para substituir o texto original
        if (errorObjs && Array.isArray(errorObjs) && errorObjs.length > 0) {
          let formattedText = "Erros no processamento:";
          let leadsList = document.createElement("ul");
          leadsList.className = "formatted-leads-errors";

          // Formata cada erro do lead
          errorObjs.forEach(function (lead) {
            let leadItem = document.createElement("li");

            // Determinar o nome a exibir
            let displayName = "";
            if (lead.name) {
              displayName = lead.name;
            } else if (lead.FirstName || lead.LastName) {
              displayName =
                (lead.FirstName || "") + " " + (lead.LastName || "");
            } else if (lead.fullName) {
              displayName = lead.fullName;
            } else {
              displayName = "Lead sem nome";
            }

            // Nome e email
            let nameSpan = document.createElement("span");
            nameSpan.className = "lead-name";
            nameSpan.textContent = displayName.trim();

            // Se tiver email, adiciona
            let emailValue = lead.email || lead.Email || "";
            if (emailValue) {
              let emailSpan = document.createElement("span");
              emailSpan.className = "lead-email";
              emailSpan.textContent = ` (${emailValue})`;
              nameSpan.appendChild(emailSpan);
            }

            leadItem.appendChild(nameSpan);

            // Adiciona os erros específicos
            const errorsArray = extractErrors(lead);

            if (errorsArray && errorsArray.length > 0) {
              let errorsList = document.createElement("ul");
              errorsList.className = "lead-errors";

              errorsArray.forEach(function (error) {
                let errorItem = document.createElement("li");
                errorItem.textContent = formatErrorMessage(error);
                errorsList.appendChild(errorItem);
              });

              leadItem.appendChild(errorsList);
            } else {
              // Se não conseguiu extrair erros específicos, mostra um erro genérico
              let genericError = document.createElement("p");
              genericError.className = "generic-error";
              genericError.textContent =
                "Erro ao processar este lead. Verifique os dados.";
              leadItem.appendChild(genericError);
            }

            leadsList.appendChild(leadItem);
          });

          // Limpa o conteúdo original e adiciona a versão formatada
          item.textContent = "";
          item.appendChild(document.createTextNode(formattedText));
          item.appendChild(leadsList);
          item.className = "formatted-error-item";

          console.log("Lista de erros formatada com sucesso");
        } else {
          // Nenhum JSON válido encontrado, tenta exibir o erro de forma mais legível
          formatPlainTextError(item, text);
        }
      } catch (e) {
        console.error("Erro ao tentar formatar JSON de erro:", e);
        // Tentar um fallback simples formatando o texto
        formatPlainTextError(item, text);
      }
    } else {
      // Não contém JSON, formata o texto simples
      formatPlainTextError(item, text);
    }
  });
}

/**
 * Formata uma mensagem de erro texto simples para melhor legibilidade
 */
function formatPlainTextError(item, text) {
  try {
    // Verifica se o texto contém "erro" ou "falha" para identificar possíveis mensagens
    const errorRegex =
      /(?:erro|falha|inválido|obrigatório)[:;-]?\s*([^\n\r.]*)/gi;
    const matches = [...text.matchAll(errorRegex)];

    if (matches && matches.length > 0) {
      let errorContainer = document.createElement("div");
      errorContainer.className = "plain-text-error";

      let errorTitle = document.createElement("p");
      errorTitle.className = "error-title";
      errorTitle.textContent = "Detalhes do erro:";
      errorContainer.appendChild(errorTitle);

      let errorList = document.createElement("ul");

      // Adicionar cada mensagem de erro encontrada
      let addedErrors = new Set();
      matches.forEach((match) => {
        if (match[1] && match[1].trim() && !addedErrors.has(match[1].trim())) {
          let errorItem = document.createElement("li");
          errorItem.textContent = match[1].trim();
          errorList.appendChild(errorItem);
          addedErrors.add(match[1].trim());
        }
      });

      // Se não encontrou mensagens específicas, mantém o texto original mas formatado
      if (addedErrors.size === 0) {
        let defaultError = document.createElement("li");
        defaultError.textContent = text.trim();
        errorList.appendChild(defaultError);
      }

      errorContainer.appendChild(errorList);

      // Substitui o conteúdo original pelo formatado
      item.textContent = "";
      item.appendChild(errorContainer);
      item.className = "plain-text-error-item";
    }
  } catch (e) {
    console.error("Erro ao formatar texto simples:", e);
    // Se falhar, apenas limpa espaços extras para melhorar um pouco a exibição
    item.textContent = text.trim();
  }
}

/**
 * Extrai mensagens de erro de um objeto de lead
 * Tenta vários formatos conhecidos que podem conter mensagens de erro
 */
function extractErrors(lead) {
  // Arrays para armazenar os erros encontrados
  let errors = [];

  // Formato comum: objeto tem uma propriedade "errors" que é um array
  if (lead.errors && Array.isArray(lead.errors)) {
    errors = errors.concat(lead.errors);
  }

  // Formato alternativo: objeto tem uma propriedade "message" ou "errorMessage"
  if (lead.message && typeof lead.message === "string") {
    errors.push(lead.message);
  }

  if (lead.errorMessage && typeof lead.errorMessage === "string") {
    errors.push(lead.errorMessage);
  }

  // Formato Salesforce: objeto tem uma propriedade "error" ou "Error"
  if (lead.error && typeof lead.error === "string") {
    errors.push(lead.error);
  }

  if (lead.Error && typeof lead.Error === "string") {
    errors.push(lead.Error);
  }

  // Procura por outros campos que contenham a palavra "error" ou "message"
  Object.keys(lead).forEach((key) => {
    if (
      (key.toLowerCase().includes("error") ||
        key.toLowerCase().includes("message")) &&
      typeof lead[key] === "string" &&
      !errors.includes(lead[key])
    ) {
      errors.push(lead[key]);
    }
  });

  return errors;
}

/**
 * Formata uma mensagem de erro para melhor legibilidade
 */
function formatErrorMessage(errorMsg) {
  if (!errorMsg) return "Erro desconhecido";

  // Remover prefixos comuns de erro
  let formatted = errorMsg.replace(/^(error|erro|falha|failure):\s*/i, "");

  // Capitalizar a primeira letra
  formatted = formatted.charAt(0).toUpperCase() + formatted.slice(1);

  // Garantir que termina com ponto final
  if (
    !formatted.endsWith(".") &&
    !formatted.endsWith("!") &&
    !formatted.endsWith("?")
  ) {
    formatted += ".";
  }

  return formatted;
}

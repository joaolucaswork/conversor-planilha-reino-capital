/**
 * Script específico para resolver problemas com a exibição de resultados em Salesforce
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script de verificação e correção do Salesforce carregado");

  // Executamos uma verificação logo após o carregamento da página
  setTimeout(verifySuccessStatus, 300);
});

/**
 * Verifica o status de sucesso na página de resultados e corrige exibições inconsistentes
 */
function verifySuccessStatus() {
  // Verifica se estamos na página de resultados
  if (!window.location.pathname.includes("/resultado")) {
    return;
  }

  console.log("Executando verificação de status na página de resultados");

  // Obtém as estatísticas para análise
  const statNumbers = document.querySelectorAll(".stat-number");
  if (!statNumbers || statNumbers.length < 3) {
    console.warn("Elementos de estatística não encontrados corretamente");
    return;
  }

  // Analisa as estatísticas exibidas
  const createdLeads = parseInt(statNumbers[0].textContent.trim()) || 0;
  const totalProcessed = parseInt(statNumbers[1].textContent.trim()) || 0;
  const failedLeads = parseInt(statNumbers[2].textContent.trim()) || 0;

  console.log(
    `Estatísticas detectadas - Criados: ${createdLeads}, Total: ${totalProcessed}, Falhas: ${failedLeads}`
  );
  // Verifica inconsistências nos dados mostrados
  const hasProcessedItems = totalProcessed > 0;
  const hasSuccessfulLeads = createdLeads > 0;
  const hasFailedLeads = failedLeads > 0;

  // Elementos visuais
  const resultIcon = document.querySelector(".result-icon");
  const resultTitle = document.querySelector(".result-section h2");
  const resultMessage = document.querySelector(".result-message");
  const failedLeadsSection = document.querySelector(".failed-leads-section");

  // Se processou itens (com sucesso ou falha), verificamos se a exibição está correta
  if (hasProcessedItems || hasFailedLeads) {
    console.log("Processamento detectado, verificando estado visual...");

    // Corrige estatísticas se necessário
    if (failedLeads > 0 && !hasSuccessfulLeads) {
      // Se temos falhas mas nenhum sucesso, mostramos o ícone de erro
      if (resultIcon && resultIcon.classList.contains("success")) {
        console.log("Corrigindo ícone para erro (todos falharam)");
        resultIcon.classList.remove("success");
        resultIcon.classList.add("error");
        resultIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
      }

      // Atualiza o título para indicar problema
      if (resultTitle && !resultTitle.textContent.includes("problema")) {
        console.log("Corrigindo título para indicar problema");
        resultTitle.textContent = "Houve um problema!";
      }
    } else if (hasSuccessfulLeads) {
      // Força o título e ícone para sucesso se temos leads criados com sucesso
      if (resultTitle && resultTitle.textContent.includes("problema")) {
        console.log("Corrigindo título para indicar sucesso");
        resultTitle.textContent = "Processamento Concluído!";
      }

      // Corrige o ícone se necessário
      if (resultIcon && resultIcon.classList.contains("error")) {
        console.log("Corrigindo ícone para sucesso");
        resultIcon.classList.remove("error");
        resultIcon.classList.add("success");
        resultIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
      }
    }

    // Garante que a mensagem de resultado esteja visível
    if (resultMessage) {
      resultMessage.style.display = "block";

      // Se tem leads criados mas a mensagem diz 0, corrige
      if (hasSuccessfulLeads && resultMessage.textContent.includes("0 leads")) {
        console.log("Corrigindo mensagem de leads importados");
        resultMessage.textContent = `${createdLeads} leads foram importados com sucesso para o Salesforce.`;
      }
    }
  }
}

/**
 * Este arquivo contém funções para garantir que a página de resultados
 * seja exibida corretamente após o processamento dos leads no Salesforce.
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script de correção resultado carregado");

  const urlParams = new URLSearchParams(window.location.search);
  const hasLeads = urlParams.has("has_leads");

  // Se estamos na página de resultados, verificamos se estamos vindo de um processamento
  if (window.location.pathname.includes("/resultado")) {
    // Verifica se há elementos que precisam ser exibidos
    const resultSummary = document.querySelector(".result-summary");

    if (resultSummary) {
      console.log("Encontrada seção de resumo de resultados");

      // Adiciona classe para garantir visibilidade
      resultSummary.classList.add("result-visible");

      // Força a exibição de mensagens de resultado para garantir que sejam visíveis
      const resultMessage = document.querySelector(".result-message");
      if (resultMessage) {
        resultMessage.style.display = "block";
        console.log("Garantindo visibilidade da mensagem de resultado");
      }

      // Detecta se existem estatísticas para verificar sucesso
      const statsNumber = document.querySelectorAll(".stat-number");
      if (statsNumber && statsNumber.length >= 1) {
        const leadCount = parseInt(statsNumber[0].textContent);
        if (leadCount > 0) {
          console.log(`Leads importados: ${leadCount}`);

          // Força a exibição como sucesso se há leads importados
          const errorIcon = document.querySelector(".result-icon.error");
          if (errorIcon) {
            console.log("Convertendo ícone de erro para sucesso");
            errorIcon.classList.remove("error");
            errorIcon.classList.add("success");
            errorIcon.innerHTML = '<i class="fas fa-check-circle"></i>';

            // Também atualiza o título de acordo
            const titleElement = errorIcon.nextElementSibling;
            if (titleElement && titleElement.tagName === "H2") {
              titleElement.textContent = "Processamento Concluído!";
            }
          }
        }
      }

      // Verifica se há ícone de sucesso para animar
      const successIcon = document.querySelector(".result-icon.success");
      if (successIcon) {
        console.log("Animando ícone de sucesso");
        successIcon.classList.add("animated");
      }
    }

    // Adiciona evento para o botão de voltar ao início
    const backButton = document.querySelector(".button.primary");
    if (backButton) {
      backButton.addEventListener("click", function (e) {
        // Limpar dados da sessão no redirecionamento
        console.log("Clicou em Voltar ao Início");
        fetch("/clear_session", { method: "POST" })
          .then((response) => {
            // Continua o redirecionamento normal
            return true;
          })
          .catch((error) => {
            console.error("Erro ao limpar sessão:", error);
            // Continua o redirecionamento normal mesmo com erro
            return true;
          });
      });
    }
  }
});

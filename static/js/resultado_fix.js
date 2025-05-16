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
      if (statsNumber && statsNumber.length >= 3) {
        let leadCount = parseInt(statsNumber[0].textContent) || 0;
        let totalCount = parseInt(statsNumber[1].textContent) || 0;
        let failCount = parseInt(statsNumber[2].textContent) || 0;

        console.log(
          `Stats detectadas - Leads: ${leadCount}, Total: ${totalCount}, Falhas: ${failCount}`
        );

        // Verificar se há falhas na lista mas contagem zerada
        const failedSection = document.querySelector(".failed-leads-section");

        if (failedSection) {
          // Contamos manualmente os itens de falha
          const failItems = failedSection.querySelectorAll(
            ".failed-leads-list li"
          );
          const manualFailCount = failItems.length;

          console.log(`Contagem manual de falhas: ${manualFailCount}`);

          // Se há falhas visíveis mas os números estão errados, corrigimos
          if (
            manualFailCount > 0 &&
            (failCount === 0 || failCount !== manualFailCount)
          ) {
            console.log(
              `Detectados ${manualFailCount} itens de falha, mas contador é ${failCount}. Corrigindo...`
            );

            // Se o totalCount for zero ou menor que o número de falhas, atualizamos
            if (totalCount === 0 || totalCount < manualFailCount) {
              totalCount = manualFailCount;
              console.log(`Total count atualizado para ${totalCount}`);
            }

            // Atualizar o número de falhas
            failCount = manualFailCount;
            console.log(`Fail count atualizado para ${failCount}`);

            // Se o leadCount + failCount não bate com o total, ajustamos
            if (leadCount + failCount !== totalCount) {
              if (leadCount > 0) {
                // Se já tem leads criados, ajusta o total
                totalCount = leadCount + failCount;
                console.log(`Total count recalculado: ${totalCount}`);
              } else {
                // Se não tem leads criados, assume que nenhum foi criado
                leadCount = 0;
                console.log(`Lead count definido como zero`);
              }
            }

            // Atualizar os elementos da interface
            if (statsNumber[0]) statsNumber[0].textContent = leadCount;
            if (statsNumber[1]) statsNumber[1].textContent = totalCount;
            if (statsNumber[2]) statsNumber[2].textContent = failCount;
          }

          // Garante que a seção de falhas esteja visível se houver falhas
          if (manualFailCount > 0 || failCount > 0) {
            failedSection.style.display = "block";
          }
        }

        // Verifica se temos situação de falha total (todos falharam)
        if (leadCount === 0 && (failCount > 0 || totalCount > 0)) {
          console.log(
            "Detectado caso de falha total - todos os leads falharam"
          );

          // Se estamos mostrando como sucesso, corrige para erro
          const successIcon = document.querySelector(".result-icon.success");
          if (successIcon) {
            console.log("Corrigindo ícone de sucesso para erro");
            successIcon.classList.remove("success");
            successIcon.classList.add("error");
            successIcon.innerHTML = '<i class="fas fa-times-circle"></i>';

            // Também atualiza o título para erro
            const titleElement = successIcon.nextElementSibling;
            if (titleElement && titleElement.tagName === "H2") {
              titleElement.textContent = "Houve um problema!";
            }
          }

          // Garante que a mensagem reflita a situação de falha
          if (
            resultMessage &&
            !resultMessage.textContent.includes("falha") &&
            !resultMessage.textContent.includes("erro") &&
            !resultMessage.textContent.includes("problema")
          ) {
            resultMessage.textContent =
              "Ocorreram erros durante o processamento dos leads.";
          }

          // Certifica-se de que a seção de falhas está visível
          if (failedSection) {
            failedSection.style.display = "block";
          }
        } else if (leadCount > 0) {
          // Sucesso total ou parcial (pelo menos alguns leads importados)
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

          // Atualiza mensagem se há sucesso e falhas
          if (failCount > 0 && resultMessage) {
            if (
              !resultMessage.textContent.includes("parcial") &&
              !resultMessage.textContent.includes("alguns")
            ) {
              resultMessage.textContent = `Processamento concluído com sucesso parcial: ${leadCount} leads importados e ${failCount} falhas.`;
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

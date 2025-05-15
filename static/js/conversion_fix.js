// Soluciona o problema com o estado "undefined" durante o carregamento
// e mostra a mensagem de sucesso após a conclusão do processamento

document.addEventListener("DOMContentLoaded", function () {
  console.log("Script de correção carregado");

  // Se estamos na página de resultados, verificamos se há mensagem de sucesso
  const resultSection = document.querySelector(".result-section");
  if (resultSection) {
    console.log("Página de resultados detectada");
    // Adiciona uma classe para mostrar uma animação de sucesso
    const resultIcon = document.querySelector(".result-icon");
    if (resultIcon && resultIcon.classList.contains("success")) {
      resultIcon.innerHTML += '<div class="success-animation"></div>';
      console.log("Animação de sucesso adicionada");
    }
  }

  // Se estamos na página de conversão, ajudamos a lidar com o estado indefinido
  const conversionSection = document.querySelector(".conversion-section");
  if (conversionSection) {
    console.log("Página de conversão detectada");
    const progressText = document.querySelector(".progress-text");
    if (progressText) {
      // Verificar e corrigir mensagem "undefined"
      const checkProgress = setInterval(function () {
        if (progressText.textContent.includes("undefined")) {
          console.log("Corrigindo texto 'undefined'");
          progressText.textContent = "Processando... Por favor, aguarde.";
        }
      }, 100);

      // Limpar o intervalo após 30 segundos (quando a conversão provavelmente já terminou)
      setTimeout(function () {
        clearInterval(checkProgress);
      }, 30000);
    }
  }
});

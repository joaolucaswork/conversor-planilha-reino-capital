/**
 * Conversor de Planilha para Salesforce - Main JavaScript
 * Simplified version that combines file_upload_fix.js, upload.js, and script.js
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("[main.js] Inicializando script");

  const uploadForm = document.getElementById("upload-form");
  const fileInput = document.getElementById("file-upload");
  const closeButtons = document.querySelectorAll(".close-button");
  const cancelButton = document.querySelector(".cancel-button");
  const conversionSection = document.getElementById("conversion-section");
  const leadOwnerSelect = document.getElementById("lead-owner");
  const customOwnerField = document.getElementById("custom-owner-id");

  // Controle da seleção de owner para os leads
  if (leadOwnerSelect) {
    leadOwnerSelect.addEventListener("change", function () {
      if (this.value === "custom") {
        customOwnerField.style.display = "block";
      } else {
        customOwnerField.style.display = "none";
      }
    });
  }

  // File upload form validation
  if (uploadForm && fileInput) {
    uploadForm.addEventListener("submit", function (event) {
      // Validate file selection
      if (!fileInput.files || fileInput.files.length === 0) {
        event.preventDefault();
        alert("Por favor, selecione um arquivo antes de enviar.");
        return false;
      }

      // Verify file extension
      const fileName = fileInput.files[0].name;
      const fileExt = fileName.split(".").pop().toLowerCase();

      if (!["csv", "xlsx", "xls", "txt"].includes(fileExt)) {
        event.preventDefault();
        alert(
          "Por favor, selecione um arquivo com extensão .csv, .xlsx, .xls ou .txt"
        );
        return false;
      }

      // Add loading state to button
      const uploadBtn = document.querySelector(".btn");
      uploadBtn.innerHTML =
        '<i class="fas fa-spinner fa-spin"></i> Enviando arquivo...';
      uploadBtn.disabled = true;

      // Show conversion section for Excel files and TXT files
      if (["xlsx", "xls", "txt"].includes(fileExt)) {
        // Show the conversion section
        conversionSection.style.display = "block";

        // Start the progress animation
        animateProgress();

        // Check conversion status periodically
        conversionPolling = setInterval(checkConversionStatus, 1000);
      }

      return true;
    });
  }

  // File upload area interaction
  if (fileInput) {
    const fileUploadArea = document.querySelector(".file-upload-area");

    if (fileUploadArea) {
      fileUploadArea.addEventListener("click", function () {
        fileInput.click();
      });
    }

    fileInput.addEventListener("change", function () {
      if (this.files && this.files.length > 0) {
        // Show the file name in the label
        const label = document.querySelector(".file-upload-area label");
        if (label) {
          label.textContent = this.files[0].name;
        }

        // Enable submit button
        const uploadButton = document.getElementById("upload-button");
        if (uploadButton) {
          uploadButton.disabled = false;
        }
      }
    });
  }

  // Close button handlers
  closeButtons.forEach((button) => {
    button.addEventListener("click", function () {
      if (conversionSection) {
        conversionSection.style.display = "none";
      }
    });
  });

  // Cancel button handler
  if (cancelButton) {
    cancelButton.addEventListener("click", function () {
      if (conversionSection) {
        conversionSection.style.display = "none";
      }
      resetForm();
    });
  }

  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.opacity = "0";
      setTimeout(() => {
        alert.style.display = "none";
      }, 500);
    }, 5000);
  });
});

// Function to animate the progress circle
function animateProgress() {
  let progress = 0;
  const progressRing = document.querySelector(".progress-ring-circle");
  const progressText = document.querySelector(".progress-percentage");
  const circumference = 326.726; // 2πr

  const interval = setInterval(() => {
    progress += 1;

    if (progress > 100) {
      clearInterval(interval);
      return;
    }

    // Update progress ring
    if (progressRing) {
      const offset = circumference * (1 - progress / 100);
      progressRing.style.strokeDashoffset = offset;
    }

    // Update percentage text
    if (progressText) {
      progressText.textContent = `${progress}%`;
    }
  }, 50);
}

// Function to check conversion status from server
function checkConversionStatus() {
  fetch("/check_conversion")
    .then((response) => response.json())
    .then((data) => {
      // Handle when data.status is not defined - show a generic processing message
      if (!data.status && data !== "not_found") {
        updateProgress(50); // Use default 50% progress when no status is available
        return;
      }

      // Update conversion UI with status
      if (data.status === "completed") {
        clearInterval(conversionPolling);
        // Redirect to results page or update UI as needed
        window.location.href = data.redirect_url || "/resultado";
      } else if (data.status === "failed") {
        clearInterval(conversionPolling);
        showConversionError();
      } else {
        // Update progress if processing
        updateProgress(data.progress);
      }
    })
    .catch((error) => {
      console.error("Erro ao verificar status da conversão:", error);
    });
}

// Function to update progress display
function updateProgress(progress) {
  const progressText = document.querySelector(".progress-text");
  const progressRing = document.querySelector(".progress-ring-circle");
  const progressPercentage = document.querySelector(".progress-percentage");

  // Set a default progress value if undefined
  if (progress === undefined || progress === null) {
    progress = 50;
    console.log(
      "Valor de progresso indefinido, usando valor padrão:",
      progress
    );
  }

  if (progressText) {
    progressText.textContent = `Processando... (${progress}%)`;
    console.log("Atualizado texto de progresso:", progressText.textContent);
  }

  if (progressRing && progressPercentage) {
    const circumference = 326.726;
    const offset = circumference * (1 - progress / 100);
    progressRing.style.strokeDashoffset = offset;
    progressPercentage.textContent = `${progress}%`;
  }
}

// Function to show conversion error
function showConversionError() {
  const progressText = document.querySelector(".progress-text");
  if (progressText) {
    progressText.textContent =
      "Ocorreu um erro ao processar o arquivo. Por favor, tente novamente.";
    progressText.style.color = "var(--danger-color)";
  }
}

// Function to reset the form
function resetForm() {
  const uploadForm = document.getElementById("upload-form");
  const uploadButton = document.getElementById("upload-button");

  if (uploadForm) {
    uploadForm.reset();
  }

  if (uploadButton) {
    uploadButton.disabled = false;
    uploadButton.innerHTML = '<i class="fas fa-upload"></i> Enviar';
  }

  const fileLabel = document.querySelector(".file-upload-area label");
  if (fileLabel) {
    fileLabel.textContent = "Selecione um arquivo";
  }
}

// Global variable for conversion polling
let conversionPolling = null;

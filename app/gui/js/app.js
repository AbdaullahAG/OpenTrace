const uploadSection = document.getElementById("upload-section");
const loadingSection = document.getElementById("loading-section");
const resultsSection = document.getElementById("results-section");

const selectFileBtn = document.getElementById("select-file-btn");
const startOverBtn = document.getElementById("start-over-btn");
const loadingStatus = document.getElementById("loading-status");
const insightBox = document.getElementById("llm-insight-box");

function showScreen(screenToShow) {
  uploadSection.classList.remove("active");
  uploadSection.classList.add("hidden");

  loadingSection.classList.remove("active");
  loadingSection.classList.add("hidden");

  resultsSection.classList.remove("active");
  resultsSection.classList.add("hidden");

  screenToShow.classList.remove("hidden");
  screenToShow.classList.add("active");
}

selectFileBtn.addEventListener("click", async () => {
  showScreen(loadingSection);
  loadingStatus.textContent = "Asking you to select a file...";

  const response = await BackendAPI.analyzeWatchHistory();

  if (response.success) {
    insightBox.innerHTML = response.message;
    showScreen(resultsSection);
  } else {
    alert(response.message || "Something went wrong.");
    showScreen(uploadSection);
  }
});

startOverBtn.addEventListener("click", () => {
  showScreen(uploadSection);
});

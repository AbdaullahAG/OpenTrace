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

const dropZone = document.getElementById("drop-zone");

// --- Core Analysis Function ---
// Reused for both the Browse button and the Drag-and-Drop action
async function processTakeoutPath(selectedPath) {
  showScreen(loadingSection);
  loadingStatus.textContent =
    "Extracting and analyzing data... This may take a moment.";

  try {
    const response = await window.pywebview.api.run_analysis(selectedPath);

    if (response && response.success) {
      insightBox.innerHTML = response.report;
      showScreen(resultsSection);
    } else {
      alert(response?.message || "Something went wrong during analysis.");
      showScreen(uploadSection);
    }
  } catch (error) {
    console.error("Bridge Error Details:", error);
    alert("Failed to communicate with Python backend. Check the console!");
    showScreen(uploadSection);
  }
}

// --- 1. Button Click Handler ---
selectFileBtn.addEventListener("click", async () => {
  try {
    const selectedPath = await window.pywebview.api.select_takeout_path();
    if (selectedPath) {
      await processTakeoutPath(selectedPath);
    }
  } catch (error) {
    console.error("Error opening folder picker:", error);
  }
});

// --- 2. Drag and Drop Logic ---
// Prevent default browser behaviors (which normally try to open the file in a new tab)
["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, preventDefaults, false);
  document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

// Add visual highlight when dragging over the box
["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(
    eventName,
    () => dropZone.classList.add("dragover"),
    false,
  );
});

// Remove highlight when dragged away or dropped
["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(
    eventName,
    () => dropZone.classList.remove("dragover"),
    false,
  );
});

// Handle the actual file drop
dropZone.addEventListener(
  "drop",
  (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;

    if (files && files.length > 0) {
      // PyWebView's Chromium engine securely exposes the absolute system path via the 'path' property
      const droppedPath = files[0].path;

      if (droppedPath) {
        processTakeoutPath(droppedPath);
      } else {
        alert(
          "Could not read the folder path automatically. Please use the Browse button instead.",
        );
      }
    }
  },
  false,
);

startOverBtn.addEventListener("click", () => {
  showScreen(uploadSection);
});

const cursorDot = document.getElementById("cursor-dot");
const cursorOutline = document.getElementById("cursor-outline");
const cursorShadow = document.getElementById("cursor-shadow");
const guideOverlay = document.getElementById("guide-overlay");
const guideTipBox = document.getElementById("guide-tip-box");
const guidePath = document.getElementById("guide-path");

let currentStep = 0;
const steps = [
  { target: "select-file-btn", message: "Tip: click here" },
  { target: "start-over-btn", message: "Tip: click here" },
];

let mouseX = window.innerWidth / 2;
let mouseY = window.innerHeight / 2;
let shadowInterval;

function updateGuide() {
  clearInterval(shadowInterval);

  if (currentStep >= steps.length) {
    guideOverlay.classList.add("hidden");
    cursorShadow.style.opacity = "0";
    return;
  }

  const targetElement = document.getElementById(steps[currentStep].target);
  if (!targetElement || targetElement.closest(".screen.hidden")) {
    guideOverlay.classList.add("hidden");
    cursorShadow.style.opacity = "0";
    return;
  }

  guideOverlay.classList.remove("hidden");
  guideTipBox.textContent = steps[currentStep].message;

  const rect = targetElement.getBoundingClientRect();

  const tipX = Math.max(20, rect.left - 380);
  const tipY = Math.max(20, rect.top - 100);

  guideTipBox.style.left = `${tipX}px`;
  guideTipBox.style.top = `${tipY}px`;

  const startX = tipX + 90;
  const startY = tipY + 65;
  const endX = rect.left - 15;
  const endY = rect.top + rect.height / 2;
  const cpX = tipX - 30;
  const cpY = endY + 20;

  guidePath.setAttribute(
    "d",
    `M ${startX} ${startY} Q ${cpX} ${cpY} ${endX} ${endY}`,
  );

  shadowInterval = setInterval(() => {
    const targetX = rect.left + rect.width / 2;
    const targetY = rect.top + rect.height / 2;

    cursorShadow.animate(
      [
        {
          transform: `translate(${mouseX - 10}px, ${mouseY - 10}px) scale(1)`,
          opacity: 0,
        },
        {
          transform: `translate(${mouseX - 10}px, ${mouseY - 10}px) scale(1)`,
          opacity: 0.6,
          offset: 0.1,
        },
        {
          transform: `translate(${targetX - 10}px, ${targetY - 10}px) scale(2)`,
          opacity: 0,
          offset: 1,
        },
      ],
      {
        duration: 1500,
        easing: "cubic-bezier(0.25, 1, 0.5, 1)",
      },
    );
  }, 2000);
}

window.addEventListener("mousemove", function (e) {
  mouseX = e.clientX;
  mouseY = e.clientY;

  cursorDot.style.left = `${mouseX}px`;
  cursorDot.style.top = `${mouseY}px`;

  cursorOutline.animate(
    {
      left: `${mouseX}px`,
      top: `${mouseY}px`,
    },
    { duration: 500, fill: "forwards" },
  );
});

document.querySelectorAll("button").forEach((button) => {
  button.addEventListener("mouseenter", () => {
    document.body.classList.add("cursor-hover");
  });
  button.addEventListener("mouseleave", () => {
    document.body.classList.remove("cursor-hover");
  });
});

let originalShowScreen =
  typeof showScreen !== "undefined" ? showScreen : function () {};
showScreen = function (screenToShow) {
  originalShowScreen(screenToShow);
  setTimeout(updateGuide, 100);
};

updateGuide();

window.startDeepAnalysis = async function () {
  insightBox.innerHTML =
    '<div class="spinner"></div><p style="text-align:center; margin-top:15px;">Running local LLM analysis. This will take a moment...</p>';

  const response = await window.pywebview.api.triggerLLMAnalysis();

  if (response.success) {
    insightBox.innerHTML = response.message;
  } else {
    insightBox.innerHTML = `<p style="color:red;">Error: ${response.message}</p>`;
  }
};

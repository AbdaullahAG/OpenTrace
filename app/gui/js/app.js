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

/** Render the BubbleReport object into the results section. */
function renderReport(report) {
  const score = report.bubble_score ?? 0;
  const flags = report.manipulation_flags ?? [];
  const alts  = report.suggested_alternatives ?? [];
  const meta  = report.metadata ?? {};

  const flagLabels = {
    low_source_diversity:     "مصادرك محدودة جداً",
    high_topic_concentration: "محتواك متركّز حول موضوع واحد",
    high_algorithmic_exposure:"معظم ما تشاهده من قنوات لم تشترك بها",
    single_channel_dominance: "قناة واحدة تهيمن على مشاهداتك",
  };

  const flagsHTML = flags.length
    ? `<ul>${flags.map(f => `<li>${flagLabels[f] || f}</li>`).join("")}</ul>`
    : `<p>لم يتم رصد مؤشرات خطر واضحة.</p>`;

  const altsHTML = alts.length
    ? alts.map(a =>
        `<li><a href="${a.url}" target="_blank"><strong>${a.name}</strong></a> — ${a.description}
         <br><small style="color:#888">${a.reason}</small></li>`
      ).join("")
    : "";

  insightBox.innerHTML = `
    <h3>درجة فقاعتك: <span style="color:${score > 60 ? '#c0392b' : score > 35 ? '#e67e22' : '#27ae60'}">${score} / 100</span></h3>
    <hr style="margin:12px 0">
    <h4>مؤشرات التأثير:</h4>
    ${flagsHTML}
    ${altsHTML ? `<h4 style="margin-top:16px">بدائل مقترحة:</h4><ul>${altsHTML}</ul>` : ""}
    <p style="margin-top:16px;font-size:0.85rem;color:#999">
      حُلِّل ${meta.total_items ?? "?"} فيديو
      ${meta.sampled_for_ai ? `(عيّنة ${meta.sample_size} للذكاء الاصطناعي)` : ""}
    </p>
  `;
}

// --- Button Click Handler ---
selectFileBtn.addEventListener("click", async () => {
  // Step 1: open the native file picker (shows .zip files)
  loadingStatus.textContent = "Opening file picker...";
  showScreen(loadingSection);

  const path = await BackendAPI.selectFile();

  if (!path) {
    // User cancelled the dialog — go back silently
    showScreen(uploadSection);
    return;
  }

  // Step 2: run the full analysis pipeline
  loadingStatus.textContent = "Extracting and analyzing data... This may take a moment.";

  const response = await BackendAPI.runAnalysis(path);

  if (response.success) {
    renderReport(response.report);
    showScreen(resultsSection);
  } else {
    alert(response.message || "Something went wrong.");
    showScreen(uploadSection);
  }
});

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

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
  const alts = report.suggested_alternatives ?? [];
  const meta = report.metadata ?? {};

  const scoreColor =
    score > 60 ? "#c0392b" : score > 35 ? "#e67e22" : "#27ae60";
  const scoreBg = score > 60 ? "#fdf2f2" : score > 35 ? "#fff9f2" : "#f0fdf4";

  const flagLabels = {
    low_source_diversity: "مصادرك محدودة جداً",
    high_topic_concentration: "محتواك متركّز حول موضوع واحد",
    high_algorithmic_exposure: "معظم ما تشاهده من قنوات لم تشترك بها",
    single_channel_dominance: "قناة واحدة تهيمن على مشاهداتك",
  };

  const flagsHTML = flags.length
    ? `<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        ${flags
          .map(
            (f) => `
          <div style="background: #f8f9fa; border-right: 4px solid #c0392b; padding: 12px 15px; border-radius: 8px; font-weight: 500; color: #333;">
            🚨 ${flagLabels[f] || f}
          </div>`,
          )
          .join("")}
       </div>`
    : `<div style="background: #f0fdf4; padding: 12px; border-radius: 8px; color: #27ae60; font-weight: 500;">
         ✨ لم يتم رصد مؤشرات خطر واضحة. فقاعتك صحية!
       </div>`;

  const altsHTML = alts.length
    ? `<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        ${alts
          .map(
            (a) => `
          <div style="background: #f4f7f9; border-right: 4px solid #0056b3; padding: 15px; border-radius: 8px;">
            <a href="${a.url}" target="_blank" style="text-decoration: none; color: #0056b3; font-weight: bold; font-size: 16px;">
              🔗 ${a.name}
            </a>
            <p style="margin: 8px 0 0 0; color: #444; line-height: 1.5;">${a.description}</p>
            <small style="color: #666; display: block; margin-top: 8px; background: #e9ecef; padding: 6px; border-radius: 4px;">
              💡 <strong>لماذا؟</strong> ${a.reason}
            </small>
          </div>`,
          )
          .join("")}
       </div>`
    : "";

  insightBox.innerHTML = `
    <div dir="rtl" style="text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
      <div style="background: ${scoreBg}; border: 2px solid ${scoreColor}; border-radius: 12px; padding: 25px; text-align: center; margin-bottom: 30px;">
        <h3 style="margin: 0 0 10px 0; color: #333; font-size: 20px;">درجة فقاعتك الخوارزمية</h3>
        <div style="direction: ltr; font-size: 48px; font-weight: 900; color: ${scoreColor}; display: inline-block;">
          ${score} <span style="font-size: 20px; color: #777; font-weight: 600;">/ 100</span>
        </div>
      </div>
      <h4 style="color: #222; margin-bottom: 5px; font-size: 18px;">مؤشرات التأثير:</h4>
      ${flagsHTML}
      ${altsHTML ? `<h4 style="color: #222; margin-top: 30px; margin-bottom: 5px; font-size: 18px;">بدائل مقترحة:</h4>${altsHTML}` : ""}
      <div style="margin-top: 35px; padding-top: 15px; border-top: 2px dashed #e1e4e8; text-align: center; font-size: 13px; color: #888;">
        📊 حُلِّل <strong>${meta.total_items ?? "?"}</strong> فيديو
        ${meta.sampled_for_ai ? `<br>(تم استخدام عيّنة من ${meta.sample_size} فيديو للذكاء الاصطناعي)` : ""}
      </div>
    </div>
  `;
}

// --- Button Click Handler ---
selectFileBtn.addEventListener("click", async () => {
  try {
    if (
      typeof window.pywebview === "undefined" ||
      typeof window.pywebview.api === "undefined"
    ) {
      throw new Error("PyWebView API is not loaded.");
    }

    loadingStatus.textContent = "Opening file picker...";
    showScreen(loadingSection);

    const path = await window.pywebview.api.select_takeout_path();

    if (!path) {
      showScreen(uploadSection);
      return;
    }

    loadingStatus.textContent =
      "Extracting and analyzing data... This may take a moment.";

    await new Promise((resolve) => setTimeout(resolve, 150));

    const response = await window.pywebview.api.run_analysis(path);

    if (response && response.success) {
      renderReport(response.report);
      currentStep = 1; // Advance the tutorial arrow!
      showScreen(resultsSection);
    } else {
      alert(response?.message || "Something went wrong.");
      showScreen(uploadSection);
    }
  } catch (error) {
    console.error("Bridge Error Details:", error);
    alert("Failed to communicate with Python backend. Check the console!");
    showScreen(uploadSection);
  }
});

startOverBtn.addEventListener("click", () => {
  currentStep = 0; // Reset the tutorial arrow!
  showScreen(uploadSection);
});

// --- RESTORED & FIXED: Grandma-Friendly Tutorial Guide ---
let currentStep = 0;
const steps = [
  { target: "select-file-btn", message: "Tip: click here" },
  {
    target: "start-over-btn",
    message: "Want to analyze another file? Click here!",
  },
];

const guideOverlay = document.getElementById("guide-overlay");
const guideTipBox = document.getElementById("guide-tip-box");
const guidePath = document.getElementById("guide-path");
let shadowInterval;

function updateGuide() {
  clearInterval(shadowInterval);

  if (currentStep >= steps.length) {
    guideOverlay.classList.add("hidden");
    if (document.getElementById("tutorial-shadow"))
      document.getElementById("tutorial-shadow").style.opacity = "0";
    return;
  }

  const targetElement = document.getElementById(steps[currentStep].target);

  // FIXED: offsetHeight check prevents minimize bug
  if (
    !targetElement ||
    targetElement.closest(".screen.hidden") ||
    targetElement.offsetHeight === 0
  ) {
    guideOverlay.classList.add("hidden");
    if (document.getElementById("tutorial-shadow"))
      document.getElementById("tutorial-shadow").style.opacity = "0";
    return;
  }

  guideOverlay.classList.remove("hidden");
  guideTipBox.textContent = steps[currentStep].message;

  // FIXED: No scrollX or scrollY so the tip anchors perfectly to the fixed window view
  const rect = targetElement.getBoundingClientRect();

  // FIXED: Pushed leftOffset much further left (580) for the second screen
  const leftOffset = currentStep === 1 ? 580 : 380;
  const tipX = Math.max(20, rect.left - leftOffset);
  const tipY = Math.max(20, rect.top - 100);

  guideTipBox.style.left = `${tipX}px`;
  guideTipBox.style.top = `${tipY}px`;

  const arrowStartOffset = currentStep === 1 ? 220 : 90;
  const startX = tipX + arrowStartOffset;
  const startY = tipY + 65;

  const endX = rect.left - 15;
  const endY = rect.top + rect.height / 2;
  const cpX = tipX - 30;
  const cpY = endY + 20;

  guidePath.setAttribute(
    "d",
    `M ${startX} ${startY} Q ${cpX} ${cpY} ${endX} ${endY}`,
  );

  // FIXED: Generate a dedicated tutorial shadow so it doesn't fight Claude's script
  let tutShadow = document.getElementById("tutorial-shadow");
  if (!tutShadow) {
    tutShadow = document.createElement("div");
    tutShadow.id = "tutorial-shadow";
    tutShadow.style.cssText =
      "position:fixed; top:0; left:0; width:120px; height:120px; border-radius:50%; background:radial-gradient(circle, rgba(91, 110, 245, 0.4), transparent 70%); filter:blur(4px); pointer-events:none; z-index:9996; opacity:0;";
    document.body.appendChild(tutShadow);
  }

  // Re-enable the pulsing cursor shadow over the target button
  shadowInterval = setInterval(() => {
    const targetX = rect.left + rect.width / 2;
    const targetY = rect.top + rect.height / 2;

    // Get the current mouse position from Claude's ambient dot to start the animation
    const dot = document.getElementById("cursor-dot");
    let startMouseX = targetX;
    let startMouseY = targetY;

    if (dot && dot.style.left) {
      startMouseX = parseFloat(dot.style.left);
      startMouseY = parseFloat(dot.style.top);
    }

    tutShadow.animate(
      [
        {
          transform: `translate(${startMouseX - 60}px, ${startMouseY - 60}px) scale(0.5)`,
          opacity: 0,
        },
        {
          transform: `translate(${startMouseX - 60}px, ${startMouseY - 60}px) scale(0.5)`,
          opacity: 0.6,
          offset: 0.1,
        },
        {
          transform: `translate(${targetX - 60}px, ${targetY - 60}px) scale(1.5)`,
          opacity: 0,
          offset: 1,
        },
      ],
      { duration: 1500, easing: "cubic-bezier(0.25, 1, 0.5, 1)" },
    );
  }, 2000);
}

window.addEventListener("scroll", updateGuide);
window.addEventListener("resize", updateGuide);

// Hook into showScreen so the guide recalculates perfectly when switching screens
let originalShowScreen =
  typeof showScreen !== "undefined" ? showScreen : function () {};
showScreen = function (screenToShow) {
  originalShowScreen(screenToShow);
  setTimeout(updateGuide, 100);
};

// Initialize the guide on load
updateGuide();

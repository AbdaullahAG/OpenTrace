"use strict";

/**
 * OpenTrace Frontend Application Logic
 *
 * Security Profile (OWASP Compliant):
 * - Strict Mode enabled to prevent global namespace pollution.
 * - Strict contextual output encoding applied to all dynamic content (DOM-based XSS prevention).
 * - URL sanitization enforces safe protocols (SSRF and open redirect prevention).
 * - DOM manipulation relies exclusively on sanitized inputs.
 */

const uploadSection = document.getElementById("upload-section");
const loadingSection = document.getElementById("loading-section");
const metadataSection = document.getElementById("metadata-section");
const resultsSection = document.getElementById("results-section");

const selectFileBtn = document.getElementById("select-file-btn");
const startAnalysisBtn = document.getElementById("start-analysis-btn");
const startOverBtn = document.getElementById("start-over-btn");

const loadingStatus = document.getElementById("loading-status");
const metadataList = document.getElementById("metadata-list");
const insightBox = document.getElementById("llm-insight-box");

let selectedFilePath = "";
let currentStep = 0;

/**
 * OWASP A03:2021 - Injection Prevention
 * Contextual output encoding for HTML entities to prevent XSS.
 *
 * @param {string} value - The untrusted input string.
 * @returns {string} - Safe HTML-encoded string.
 */
function escapeHTML(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return text.replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#39;";
      default:
        return ch;
    }
  });
}

/**
 * OWASP A01:2021 - Broken Access Control / SSRF Prevention
 * Enforces safe URI schemes for external links.
 *
 * @param {string} url - The untrusted URL string.
 * @returns {string} - Sanitized URL or fallback hash.
 */
function sanitizeUrl(url) {
  try {
    const parsed = new URL(String(url), window.location.href);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.href;
    }
  } catch (_) {}
  return "#";
}

function showScreen(screenToShow) {
  uploadSection.classList.remove("active");
  uploadSection.classList.add("hidden");

  loadingSection.classList.remove("active");
  loadingSection.classList.add("hidden");

  if (metadataSection) {
    metadataSection.classList.remove("active");
    metadataSection.classList.add("hidden");
  }

  resultsSection.classList.remove("active");
  resultsSection.classList.add("hidden");

  screenToShow.classList.remove("hidden");
  screenToShow.classList.add("active");
}

function renderReport(report) {
  const score = report.bubble_score ?? 0;
  const flags = report.manipulation_flags ?? [];
  const alts = report.suggested_alternatives ?? [];
  const meta = report.metadata ?? {};

  const totalWatched = meta.exposure_total || meta.total_items || 0;
  const exposureUnsub = meta.exposure_unsubscribed || 0;
  const exposureSub = totalWatched > 0 ? totalWatched - exposureUnsub : 0;
  const unsubPercentage =
    totalWatched > 0 ? Math.round((exposureUnsub / totalWatched) * 100) : 0;
  const uniqueChannels = meta.unique_channels || 0;
  const analysisDays = meta.analysis_period_days || 0;

  const topics = report.topic_distribution || {};
const topicLabels = {
  politics: "سياسة",
  sports: "رياضة",
  entertainment: "ترفيه",
  technology: "تكنولوجيا",
  news: "أخبار",
  education: "تعليم",
  music: "موسيقى",
  gaming: "ألعاب",
  religion: "دين",
  software_engineering: "هندسة برمجيات",
  combat_fitness: "رياضات قتالية ولياقة",
  literature_philosophy: "أدب وفلسفة",
  board_games: "ألعاب استراتيجية",
  language_learning: "تعلم اللغات",
  other: "أخرى",
};

  const topicsSorted = Object.entries(topics).sort((a, b) => b[1] - a[1]);
  const classifiedTotal = topicsSorted.reduce(
    (sum, [, count]) => sum + count,
    0,
  );
  const wasSampled = meta.sampled_for_ai === true;

  let dominantHTML = "";
  if (topicsSorted.length > 0 && classifiedTotal > 0) {
    let dominantTopic = topicsSorted[0][0];
    let dominantCount = topicsSorted[0][1];

    if (dominantTopic === "other" && topicsSorted.length > 1) {
      dominantTopic = topicsSorted[1][0];
      dominantCount = topicsSorted[1][1];
    }

    const percentage = Math.round((dominantCount / classifiedTotal) * 100);
    const topicName = topicLabels[dominantTopic] || dominantTopic;
    const sampleNote = wasSampled
      ? ` (من عيّنة ${classifiedTotal} فيديو من أصل ${totalWatched})`
      : "";

    dominantHTML = `
      <div style="background: var(--report-small-bg, rgba(91, 110, 245, 0.08)); backdrop-filter: blur(10px); color: var(--report-accent-rose, #e0435f); padding: 16px 18px; border-radius: 16px; border-right: 4px solid var(--report-accent-rose, #e0435f); margin-bottom: 25px; font-size: 16px; text-align: right;">
        <strong>هيمنة المحتوى:</strong> محتواك يتمركز حول (<strong>${escapeHTML(topicName)}</strong>) بنسبة ${percentage}%${escapeHTML(sampleNote)} من إجمالي ${escapeHTML(totalWatched)} فيديو شاهدتها خلال ${escapeHTML(analysisDays)} يوما.
      </div>
    `;
  }

  const statsGridHTML = `
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 14px; margin-bottom: 30px; text-align: center;">
      <div style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); backdrop-filter: blur(10px); padding: 16px; border-radius: 16px; border: 1px solid var(--report-border, rgba(0, 0, 0, 0.08));">
        <div style="font-size: 24px; font-weight: 800; color: var(--report-text-main, #2c3e50);">${escapeHTML(totalWatched)}</div>
        <div style="font-size: 13px; color: var(--report-text-muted, #7f8c8d); margin-top: 5px;">إجمالي المشاهدات</div>
      </div>
      <div style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); backdrop-filter: blur(10px); padding: 16px; border-radius: 16px; border: 1px solid var(--report-border, rgba(0, 0, 0, 0.08));">
        <div style="font-size: 24px; font-weight: 800; color: var(--report-accent-rose, #e0435f);">${escapeHTML(unsubPercentage)}%</div>
        <div style="font-size: 13px; color: var(--report-text-muted, #7f8c8d); margin-top: 5px;">خارج اشتراكاتك</div>
      </div>
      <div style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); backdrop-filter: blur(10px); padding: 16px; border-radius: 16px; border: 1px solid var(--report-border, rgba(0, 0, 0, 0.08));">
        <div style="font-size: 24px; font-weight: 800; color: var(--report-accent-teal, #2f9d86);">${escapeHTML(exposureSub)}</div>
        <div style="font-size: 13px; color: var(--report-text-muted, #7f8c8d); margin-top: 5px;">من اشتراكاتك</div>
      </div>
      <div style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); backdrop-filter: blur(10px); padding: 16px; border-radius: 16px; border: 1px solid var(--report-border, rgba(0, 0, 0, 0.08));">
        <div style="font-size: 24px; font-weight: 800; color: var(--report-accent-purple, #7c5cf0);">${escapeHTML(uniqueChannels)}</div>
        <div style="font-size: 13px; color: var(--report-text-muted, #7f8c8d); margin-top: 5px;">قناة فريدة</div>
      </div>
    </div>
  `;

  let topicsHTML = "";
  if (topicsSorted.length > 0) {
    const topicsSampleNote = wasSampled
      ? ` <span style="font-size:13px;font-weight:normal;color:var(--report-text-muted,#7f8c8d);">(عيّنة ${escapeHTML(classifiedTotal)} من ${escapeHTML(totalWatched)})</span>`
      : "";
    const deadlineDropped = meta.classification_deadline_dropped || 0;
    const classificationFailed = meta.classification_failed || 0;
    const unresolvedCount = deadlineDropped + classificationFailed;

    const unresolvedNote =
      unresolvedCount > 0
        ? `<p style="font-size: 13px; color: var(--report-text-muted, #7f8c8d); margin: 6px 0 0 0;">
           ⏱️ ${escapeHTML(unresolvedCount)} من العناصر لم يتم تصنيفها بنجاح وتم وضعها ضمن "أخرى".
         </p>`
        : "";

    topicsHTML = `<h4 style="color: var(--report-text-main, #222); margin-top: 30px; margin-bottom: 10px; font-size: 18px;">التوزيع الكمي للتصنيفات:${topicsSampleNote}</h4>
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 25px;">
      ${topicsSorted
        .map(
          ([topic, count]) => `
        <div style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); padding: 8px 12px; border-radius: 20px; font-size: 14px; border: 1px solid var(--report-border, rgba(0, 0, 0, 0.08)); color: var(--report-text-main, #333);">
          <strong>${escapeHTML(topicLabels[topic] || topic)}</strong>: ${escapeHTML(count)}
        </div>
      `,
        )
        .join("")}
    </div>
    ${unresolvedNote}`;
  }

  const channels = report.top_channels || [];
  let channelsHTML = "";
  if (channels.length > 0) {
    channelsHTML = `<h4 style="color: var(--report-text-main, #222); margin-bottom: 10px; font-size: 18px;">القنوات الأكثر مشاهدة:</h4>
    <div style="margin-bottom: 30px;">
      <ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px;">
        ${channels
          .map(
            (c) => `
          <li style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); backdrop-filter: blur(10px); padding: 10px 15px; border-radius: 14px; border-right: 4px solid var(--primary-color, #5b6ef5); display: flex; justify-content: space-between; align-items: center; color: var(--report-text-main, #333);">
            <span style="font-weight: 500; word-break: break-word;">${escapeHTML(c.name)}</span>
            <span style="background: var(--report-small-bg, rgba(91, 110, 245, 0.08)); padding: 4px 8px; border-radius: 8px; font-size: 12px; font-weight: bold; color: var(--report-text-muted, #555); white-space: nowrap;">${escapeHTML(c.count)} مشاهدة</span>
          </li>
        `,
          )
          .join("")}
      </ul>
    </div>`;
  }

  const scoreColor =
    score > 60
      ? "var(--report-accent-rose, #e0435f)"
      : score > 35
        ? "var(--report-accent-amber, #d68d2a)"
        : "var(--report-accent-teal, #2f9d86)";

  let scoreDescription =
    score <= 35
      ? "فقاعتك صحية. أنت تشاهد محتوى متنوعا ومن مصادر مختلفة."
      : score <= 60
        ? "فقاعتك متوسطة. خوارزميات التوصية بدأت تحصرك في مسارات ومواضيع محددة."
        : "فقاعتك شديدة الانغلاق. الخوارزمية تتحكم بما تراه بشكل كبير وأنت تدور في نفس الدوامة.";

  const scoreExplanationHTML = `
    <div style="text-align: center; margin-top: -5px; margin-bottom: 35px; color: var(--report-text-main, #555); font-size: 15px; line-height: 1.5; padding: 0 20px;">
      <p style="margin: 0 0 5px 0;"><strong>ماذا يعني هذا الرقم؟</strong></p>
      <p style="margin: 0;">يقيس هذا الرقم مدى انغلاقك داخل فقاعة خوارزمية. 
      <br><span style="color: ${scoreColor}; font-weight: bold;">${escapeHTML(scoreDescription)}</span></p>
    </div>
  `;

  const flagLabels = {
    low_source_diversity: "مصادرك محدودة جدا ولا تعتمد على تنوع القنوات.",
    high_topic_concentration:
      "محتواك متركز حول موضوع واحد يسيطر على اقتراحاتك.",
    high_algorithmic_exposure: `سيطرة خوارزمية: شاهدت <strong>${escapeHTML(exposureUnsub)}</strong> فيديو من قنوات لم تشترك بها، مقابل <strong>${escapeHTML(exposureSub)}</strong> فيديو فقط من اشتراكاتك الفعلية.`,
    single_channel_dominance: "قناة واحدة تهيمن على مشاهداتك بالكامل.",
  };

  const flagsHTML = flags.length
    ? `<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        ${flags
          .map(
            (f) => `
          <div style="background: var(--report-alt-bg, rgba(255, 255, 255, 0.5)); backdrop-filter: blur(10px); border-right: 4px solid var(--report-accent-rose, #e0435f); padding: 12px 15px; border-radius: 14px; font-weight: 500; color: var(--report-text-main, #333); font-size: 15px;">
            🚨 ${flagLabels[f] || escapeHTML(f)}
          </div>`,
          )
          .join("")}
       </div>`
    : `<div style="background: var(--report-small-bg, rgba(91, 110, 245, 0.08)); border-right: 4px solid var(--report-accent-teal, #2f9d86); padding: 12px 15px; border-radius: 14px; color: var(--report-accent-teal, #2f9d86); font-weight: 500;">
         ✨ لم يتم رصد مؤشرات خطر واضحة. فقاعتك صحية.
       </div>`;

  const altsHTML = alts.length
    ? `
      <style>
        .alt-card {
          background: var(--report-alt-bg, rgba(255, 255, 255, 0.5));
          backdrop-filter: blur(10px);
          border-right: 4px solid var(--primary-color, #5b6ef5);
          padding: 15px;
          border-radius: 16px;
          transition: box-shadow 0.2s ease, transform 0.2s ease;
        }
        .alt-card:hover { box-shadow: 0 8px 22px -10px rgba(91, 110, 245, 0.35); transform: translateY(-2px); }
      </style>
      <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        ${alts
          .map(
            (a) => `
          <div class="alt-card">
            <a href="${sanitizeUrl(a.url)}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: var(--report-link, var(--primary-color, #5b6ef5)); font-weight: bold; font-size: 16px;">
              🔗 ${escapeHTML(a.name)}
            </a>
            <p style="margin: 8px 0 0 0; color: var(--report-text-main, #444); line-height: 1.5;">${escapeHTML(a.description)}</p>
            <small style="color: var(--report-text-muted, #666); display: block; margin-top: 8px; background: var(--report-small-bg, rgba(91, 110, 245, 0.08)); padding: 6px 8px; border-radius: 8px;">
              💡 <strong>لماذا؟</strong> ${escapeHTML(a.reason)}
            </small>
          </div>`,
          )
          .join("")}
       </div>`
    : "";

  insightBox.innerHTML = `
    <div dir="rtl" style="text-align: right; font-family: var(--font-sans, 'Reem Kufi', 'IBM Plex Sans Arabic', sans-serif);">
      <h3 style="margin: 0 0 20px 0; color: var(--report-text-main, #333); font-size: 20px; text-align: center;">درجة فقاعتك الخوارزمية</h3>
      
      <div class="bubble-container">
        <div class="soap-bubble" style="border: 2px solid ${scoreColor};">
          <div style="direction: ltr; font-size: 52px; font-weight: 900; color: ${scoreColor}; line-height: 1; text-shadow: 0 2px 10px rgba(255,255,255,0.3);">
            ${escapeHTML(score)}
          </div>
          <div style="font-size: 18px; color: var(--report-text-muted, #777); font-weight: 600; margin-top: 8px;">/ 100</div>
        </div>
        <div class="mini-bubble mb-1"></div>
        <div class="mini-bubble mb-2"></div>
        <div class="mini-bubble mb-3"></div>
      </div>
      
      ${scoreExplanationHTML}
      ${dominantHTML}

      <h4 style="color: var(--report-text-main, #222); margin-bottom: 15px; font-size: 18px;">تفاصيل الأرقام:</h4>
      ${statsGridHTML}

      <h4 style="color: var(--report-text-main, #222); margin-bottom: 5px; font-size: 18px;">الأدلة ومؤشرات التأثير:</h4>
      ${flagsHTML}
      ${topicsHTML}
      ${channelsHTML}
      ${altsHTML ? `<h4 style="color: var(--report-text-main, #222); margin-top: 30px; margin-bottom: 5px; font-size: 18px;">بدائل مقترحة لكسر الفقاعة:</h4>${altsHTML}` : ""}
    </div>
  `;
}

selectFileBtn.addEventListener("click", async () => {
  try {
    if (!window.pywebview || !window.pywebview.api) {
      throw new Error("PyWebView API integration failure.");
    }

    loadingStatus.textContent = "جارٍ فتح نافذة اختيار الملف...";
    showScreen(loadingSection);

    selectedFilePath = await window.pywebview.api.select_takeout_path();

    if (!selectedFilePath) {
      showScreen(uploadSection);
      return;
    }

    loadingStatus.textContent = "جارٍ استخراج البيانات الأولية...";
    const response = await window.pywebview.api.parse(selectedFilePath);

    if (response && response.success) {
      metadataList.innerHTML = `
        <li style="margin-bottom: 10px;">📊 إجمالي الفيديوهات المقروءة: <strong>${escapeHTML(response.stats.total_watched)}</strong></li>
        <li style="margin-bottom: 10px;">📅 فترة التحليل: <strong>${escapeHTML(response.stats.analysis_period_days)} يوماً</strong></li>
        <li style="margin-bottom: 10px;">🔔 إجمالي القنوات المشترك بها: <strong>${escapeHTML(response.stats.subscribed_channels)}</strong></li>
      `;
      currentStep = 1;
      showScreen(metadataSection);
    } else {
      alert(escapeHTML(response?.message || "حدث خطأ أثناء قراءة الملف."));
      showScreen(uploadSection);
    }
  } catch (error) {
    console.error("Initialization Error:", error);
    alert("فشل الاتصال بالخادم الخلفي.");
    showScreen(uploadSection);
  }
});

startAnalysisBtn.addEventListener("click", async () => {
  try {
    loadingStatus.textContent =
      "جارٍ تشغيل تحليل الذكاء الاصطناعي... قد يستغرق هذا بعض الوقت .";
    showScreen(loadingSection);

    const response = await window.pywebview.api.analyze(300);

    if (response && response.success) {
      renderReport(response.report);
      currentStep = 2;
      showScreen(resultsSection);
    } else {
      alert(escapeHTML(response?.message || "حدث خطأ أثناء التحليل."));
      showScreen(metadataSection);
    }
  } catch (error) {
    console.error("Analysis Execution Error:", error);
    alert("فشل الاتصال بالخادم الخلفي.");
    showScreen(metadataSection);
  }
});

startOverBtn.addEventListener("click", () => {
  currentStep = 0;
  selectedFilePath = "";
  showScreen(uploadSection);
});

const steps = [
  { target: "select-file-btn", message: "Tip: click here" },
  { target: "start-analysis-btn", message: "Tip: click here" },
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
    const existingShadow = document.getElementById("tutorial-shadow");
    if (existingShadow) existingShadow.style.opacity = "0";
    return;
  }

  const targetElement = document.getElementById(steps[currentStep].target);

  if (
    !targetElement ||
    targetElement.closest(".screen.hidden") ||
    targetElement.offsetHeight === 0
  ) {
    guideOverlay.classList.add("hidden");
    const existingShadow = document.getElementById("tutorial-shadow");
    if (existingShadow) existingShadow.style.opacity = "0";
    return;
  }

  guideOverlay.classList.remove("hidden");
  guideTipBox.textContent = steps[currentStep].message;

  const rect = targetElement.getBoundingClientRect();
  const isLastStep = currentStep === 2;
  const leftOffset = isLastStep ? 580 : 380;
  const tipX = Math.max(20, rect.left - leftOffset);
  const tipY = Math.max(20, rect.top - 100);

  guideTipBox.style.left = `${tipX}px`;
  guideTipBox.style.top = `${tipY}px`;

  const arrowStartOffset = isLastStep ? 220 : 90;
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

  let tutShadow = document.getElementById("tutorial-shadow");
  if (!tutShadow) {
    tutShadow = document.createElement("div");
    tutShadow.id = "tutorial-shadow";
    tutShadow.style.cssText =
      "position:fixed; top:0; left:0; width:120px; height:120px; border-radius:50%; background:radial-gradient(circle, rgba(91, 110, 245, 0.4), transparent 70%); filter:blur(4px); pointer-events:none; z-index:9996; opacity:0;";
    document.body.appendChild(tutShadow);
  }

  shadowInterval = setInterval(() => {
    const targetX = rect.left + rect.width / 2;
    const targetY = rect.top + rect.height / 2;
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

let originalShowScreen =
  typeof showScreen !== "undefined" ? showScreen : function () {};
showScreen = function (screenToShow) {
  originalShowScreen(screenToShow);
  setTimeout(updateGuide, 100);
};
updateGuide();

const themeToggle = document.getElementById("theme-toggle");
themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("dark-theme");
  themeToggle.textContent = document.body.classList.contains("dark-theme")
    ? "☀️ الوضع الفاتح"
    : "🌙 الوضع الداكن";
});

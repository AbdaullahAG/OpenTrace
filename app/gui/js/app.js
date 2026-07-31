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
    other: "أخرى",
  };
  const topicsSorted = Object.entries(topics).sort((a, b) => b[1] - a[1]);
  let topicsHTML = "";
  if (topicsSorted.length > 0) {
    topicsHTML = `<h4 style="color: var(--report-text-main, #222); margin-top: 30px; margin-bottom: 10px; font-size: 18px;">أبرز التصنيفات التي شاهدتها:</h4>
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 25px;">
      ${topicsSorted
        .map(
          ([topic, count]) => `
        <div style="background: var(--report-alt-bg, #f0f4f8); padding: 8px 12px; border-radius: 20px; font-size: 14px; border: 1px solid var(--report-border, #ddd); color: var(--report-text-main, #333);">
          <strong>${topicLabels[topic] || topic}</strong>: ${count}
        </div>
      `,
        )
        .join("")}
    </div>`;
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
          <li style="background: var(--report-alt-bg, #f8f9fa); padding: 10px 15px; border-radius: 8px; border-right: 4px solid #3498db; display: flex; justify-content: space-between; align-items: center; color: var(--report-text-main, #333);">
            <span style="font-weight: 500; word-break: break-word;">${c.name}</span>
            <span style="background: var(--report-small-bg, #e9ecef); padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; color: var(--report-text-muted, #555); white-space: nowrap;">${c.count} مشاهدة</span>
          </li>
        `,
          )
          .join("")}
      </ul>
    </div>`;
  }

  const scoreColor =
    score > 60 ? "#c0392b" : score > 35 ? "#e67e22" : "#27ae60";

  let scoreDescription = "";
  if (score <= 35) {
    scoreDescription = "فقاعتك صحية! أنت تشاهد محتوى متنوعاً ومن مصادر مختلفة.";
  } else if (score <= 60) {
    scoreDescription =
      "فقاعتك متوسطة. خوارزميات التوصية بدأت تحصرك في مسارات ومواضيع محددة.";
  } else {
    scoreDescription =
      "فقاعتك شديدة الانغلاق! الخوارزمية تتحكم بما تراه بشكل كبير وأنت تدور في نفس الدوامة.";
  }

  let topTopicMsg = "";
  const totalTopicCount = Object.values(topics).reduce((a, b) => a + b, 0);
  if (topicsSorted.length > 0 && totalTopicCount > 0) {
    const topTopic = topicsSorted[0][0];
    let dominantTopic = topTopic;
    let dominantCount = topicsSorted[0][1];

    if (topTopic === "other" && topicsSorted.length > 1) {
      dominantTopic = topicsSorted[1][0];
      dominantCount = topicsSorted[1][1];
    }

    const percentage = Math.round((dominantCount / totalTopicCount) * 100);
    const topicName = topicLabels[dominantTopic] || dominantTopic;

    topTopicMsg = `محتواك يتمركز حول (<strong>${topicName}</strong>) بنسبة ${percentage}%.`;
  }

  const scoreExplanationHTML = `
    <div style="text-align: center; margin-top: -5px; margin-bottom: 35px; color: var(--report-text-main, #555); font-size: 15px; line-height: 1.5; padding: 0 20px;">
      <p style="margin: 0 0 5px 0;"><strong>ماذا يعني هذا الرقم؟</strong></p>
      <p style="margin: 0;">يقيس هذا الرقم مدى انغلاقك داخل فقاعة خوارزمية. 
      <br><span style="color: ${scoreColor}; font-weight: bold;">${scoreDescription}</span>
      <br><span style="color: var(--report-text-main, #444); margin-top: 5px; display: inline-block;">${topTopicMsg}</span></p>
    </div>
  `;

  const flagLabels = {
    low_source_diversity: "مصادرك محدودة جداً",
    high_topic_concentration: "محتواك متركّز حول موضوع واحد",
    high_algorithmic_exposure: `معظم ما تشاهده من قنوات لم تشترك بها<br><span style="font-size: 13px; font-weight: normal; color: var(--report-text-muted, #666); margin-top: 4px; display: inline-block;">شاهدت ${meta.exposure_unsubscribed || 0} فيديو من قنوات لم تشترك بها مقابل ${(meta.exposure_total || 0) - (meta.exposure_unsubscribed || 0)} من اشتراكاتك الفعلية.</span>`,
    single_channel_dominance: "قناة واحدة تهيمن على مشاهداتك",
  };

  const flagsHTML = flags.length
    ? `<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        ${flags
          .map(
            (f) => `
          <div style="background: var(--report-alt-bg, #f8f9fa); border-right: 4px solid #c0392b; padding: 12px 15px; border-radius: 8px; font-weight: 500; color: var(--report-text-main, #333);">
            🚨 ${flagLabels[f] || f}
          </div>`,
          )
          .join("")}
       </div>`
    : `<div style="background: var(--report-alt-bg, #f0fdf4); padding: 12px; border-radius: 8px; color: #27ae60; font-weight: 500;">
         ✨ لم يتم رصد مؤشرات خطر واضحة. فقاعتك صحية!
       </div>`;

  const altsHTML = alts.length
    ? `<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 10px;">
        ${alts
          .map(
            (a) => `
          <div style="background: var(--report-alt-bg, #f4f7f9); border-right: 4px solid #0056b3; padding: 15px; border-radius: 8px;">
            <a href="${a.url}" target="_blank" style="text-decoration: none; color: var(--report-link, #0056b3); font-weight: bold; font-size: 16px;">
              🔗 ${a.name}
            </a>
            <p style="margin: 8px 0 0 0; color: var(--report-text-main, #444); line-height: 1.5;">${a.description}</p>
            <small style="color: var(--report-text-muted, #666); display: block; margin-top: 8px; background: var(--report-small-bg, #e9ecef); padding: 6px; border-radius: 4px;">
              💡 <strong>لماذا؟</strong> ${a.reason}
            </small>
          </div>`,
          )
          .join("")}
       </div>`
    : "";

  insightBox.innerHTML = `
    <div dir="rtl" style="text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
      <h3 style="margin: 0 0 20px 0; color: var(--report-text-main, #333); font-size: 20px; text-align: center;">درجة فقاعتك الخوارزمية</h3>
      <div style="display: flex; justify-content: center; margin-bottom: 20px;">
        <div style="background: var(--report-card-bg, rgba(255, 255, 255, 0.15)); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 2px solid ${scoreColor}; border-radius: 50%; width: 170px; height: 170px; display: flex; align-items: center; justify-content: center; flex-direction: column; box-shadow: inset 0 4px 20px rgba(255,255,255,0.1), 0 8px 32px rgba(0,0,0,0.05);">
          <div style="direction: ltr; font-size: 52px; font-weight: 900; color: ${scoreColor}; line-height: 1;">
            ${score}
          </div>
          <div style="font-size: 18px; color: var(--report-text-muted, #777); font-weight: 600; margin-top: 8px;">/ 100</div>
        </div>
      </div>
      
      ${scoreExplanationHTML}
      <h4 style="color: var(--report-text-main, #222); margin-bottom: 5px; font-size: 18px;">مؤشرات التأثير:</h4>
      ${flagsHTML}
      ${topicsHTML}
      ${channelsHTML}
      ${altsHTML ? `<h4 style="color: var(--report-text-main, #222); margin-top: 30px; margin-bottom: 5px; font-size: 18px;">بدائل مقترحة:</h4>${altsHTML}` : ""}
      
      <div style="margin-top: 35px; padding-top: 15px; border-top: 2px dashed rgba(128,128,128,0.3); text-align: center; font-size: 13px; color: var(--report-text-muted, #888);">
        📊 التحليل مبني على <strong>${meta.total_items ?? "?"} فيديو</strong> خلال <strong>${meta.analysis_period_days ?? "?"} يوماً</strong>.
        ${meta.sampled_for_ai ? `<br><span style="font-size: 11px;">(تم أخذ عيّنة تمثيلية بـ ${meta.sample_size} فيديو لتحليل الذكاء الاصطناعي)</span>` : ""}
      </div>
    </div>
  `;
}

selectFileBtn.addEventListener("click", async () => {
  try {
    if (!window.pywebview || !window.pywebview.api) {
      throw new Error("PyWebView API is not loaded.");
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
        <li style="margin-bottom: 10px;">📊 إجمالي الفيديوهات المقروءة: <strong>${response.stats.total_watched}</strong></li>
        <li style="margin-bottom: 10px;">📅 فترة التحليل: <strong>${response.stats.analysis_period_days} يوماً</strong></li>
        <li style="margin-bottom: 10px;">🔔 إجمالي القنوات المشترك بها: <strong>${response.stats.subscribed_channels}</strong></li>
      `;
      currentStep = 1;
      showScreen(metadataSection);
    } else {
      alert(response?.message || "حدث خطأ أثناء قراءة الملف.");
      showScreen(uploadSection);
    }
  } catch (error) {
    console.error("Error:", error);
    alert("فشل الاتصال بالخادم الخلفي.");
    showScreen(uploadSection);
  }
});

startAnalysisBtn.addEventListener("click", async () => {
  try {
    loadingStatus.textContent =
      "جارٍ تشغيل تحليل الذكاء الاصطناعي... قد يستغرق هذا دقيقة.";
    showScreen(loadingSection);

    const response = await window.pywebview.api.analyze(300);

    if (response && response.success) {
      renderReport(response.report);
      currentStep = 2;
      showScreen(resultsSection);
    } else {
      alert(response?.message || "حدث خطأ أثناء التحليل.");
      showScreen(metadataSection);
    }
  } catch (error) {
    console.error("Error:", error);
    alert("فشل الاتصال بالخادم الخلفي.");
    showScreen(metadataSection);
  }
});

startOverBtn.addEventListener("click", () => {
  currentStep = 0;
  selectedFilePath = "";
  showScreen(uploadSection);
});

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

  const rect = targetElement.getBoundingClientRect();
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

  if (document.body.classList.contains("dark-theme")) {
    themeToggle.textContent = "☀️ الوضع الفاتح";
  } else {
    themeToggle.textContent = "🌙 الوضع الداكن";
  }
});

const BackendAPI = {
  // Phase 1 — parse only
  async parseData(path) {
    if (window.pywebview?.api) {
      return await window.pywebview.api.parse(path);
    }
    // mock
    return {
      success: true,
      stats: {
        total_watched: 912,
        subscribed_count: 227,
        unsubscribed_count: 685,
        shorts_count: 210,
        unique_channels: 143,
        subscribed_channels: 213,
        analysis_period_days: 19,
      },
    };
  },

  // Phase 2 — AI analysis
  async runAnalysis(sample_size = 300) {
    if (window.pywebview?.api) {
      return await window.pywebview.api.analyze(sample_size);
    }
    // mock
    return {
      success: true,
      report: { bubble_score: 62 },
    };
  },
};

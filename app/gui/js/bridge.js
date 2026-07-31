/**
 * bridge.js — thin wrapper around pywebview's js_api.
 *
 * All methods return a Promise that resolves with the Python return value.
 * When running outside pywebview (plain browser), we fall back to a mock
 * so the UI can be developed without Python running.
 */

const BackendAPI = {
  /** Opens the native file-picker and returns the chosen path (or null). */
  async selectFile() {
    if (window.pywebview && window.pywebview.api) {
      return window.pywebview.api.select_takeout_path();
    }
    // Browser mock for local environment testing
    return "/mock/takeout-export.zip";
  },

  /** Opens the native folder-picker and returns the chosen path (or null). */
  async selectFolder() {
    if (window.pywebview && window.pywebview.api) {
      return window.pywebview.api.select_takeout_folder();
    }
    return "/mock/takeout-folder";
  },

  /**
   * Runs the full analysis pipeline on *path* (zip or folder).
   * Resolves with { success, report } or { success: false, message }.
   */
  async runAnalysis(path) {
    if (window.pywebview && window.pywebview.api) {
      try {
        return await window.pywebview.api.run_analysis(path);
      } catch (error) {
        return {
          success: false,
          message: "Failed to communicate with Python backend: " + error,
        };
      }
    }
    // Browser mock for local environment testing
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({
          success: true,
          report: {
            bubble_score: 62,
            diversity_score: 0.38,
            concentration_score: 0.71,
            algorithmic_exposure_score: 0.58,
            topic_distribution: {
              technology: 45,
              education: 30,
              entertainment: 15,
              other: 10,
            },
            top_channels: [
              { channel: "Tech Channel", count: 40, share: 0.27 },
              { channel: "Education Hub", count: 25, share: 0.17 },
            ],
            manipulation_flags: ["high_topic_concentration"],
            timeline: [],
            ai_available: false,
            suggested_alternatives: [
              {
                name: "Invidious",
                url: "https://invidious.io",
                description:
                  "Private YouTube front-end without recommendations.",
                reason: "Based on your interest in technology",
              },
            ],
            metadata: {
              total_items: 150,
              unique_channels: 12,
              sampled_for_ai: false,
              sample_size: 150,
            },
          },
        });
      }, 2000);
    });
  },
};

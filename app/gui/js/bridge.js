const BackendAPI = {
  async analyzeWatchHistory() {
    if (window.pywebview && window.pywebview.api) {
      try {
        const result = await window.pywebview.api.trigger_analysis();
        return result;
      } catch (error) {
        return {
          success: false,
          message: "Failed to communicate with Python backend.",
        };
      }
    } else {
      console.log("Running in browser mode. Simulating backend...");
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            success: true,
            message:
              "<h3>Analysis Complete</h3><p>Your algorithm looks pretty balanced. You have a slight filter bubble around tech tutorials, but your overall content diversity is healthy.</p>",
          });
        }, 3000);
      });
    }
  },
};

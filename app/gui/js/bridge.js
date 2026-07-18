document.addEventListener('pywebviewready', async () => {
  const input = document.getElementById('fileInput');
  const output = document.getElementById('resultOutput');

  if (!input || !output) {
    return;
  }

  input.addEventListener('change', async () => {
    const file = input.files && input.files[0];
    if (!file) {
      return;
    }

    const file_path = file.path;
    const response = await window.pywebview.api.handle_file_upload(file_path);
    output.textContent = JSON.stringify(response, null, 2);
  });
});

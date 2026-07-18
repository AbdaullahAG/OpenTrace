document.addEventListener('DOMContentLoaded', () => {
  const button = document.getElementById('startBtn');
  const status = document.getElementById('status');

  if (button && status) {
    button.addEventListener('click', () => {
      status.textContent = 'OpenTrace is ready for the next step: connect your feed export.';
    });
  }
});

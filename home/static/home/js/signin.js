document.addEventListener("DOMContentLoaded", function () {
  const errorBox = document.querySelector(".error-message"); // update this selector if needed

  if (errorBox) {
    const match = errorBox.textContent.match(/Try again in (\d+)m (\d+)s/);
    if (match) {
      let minutes = parseInt(match[1]);
      let seconds = parseInt(match[2]);
      let totalSeconds = minutes * 60 + seconds;

      const updateTimer = () => {
        if (totalSeconds <= 0) return;
        totalSeconds--;

        const m = Math.floor(totalSeconds / 60);
        const s = totalSeconds % 60;

        errorBox.innerHTML = `⏳ Too many attempts. Try again in ${m}m ${s.toString().padStart(2, "0")}s.`;

        if (totalSeconds > 0) {
          setTimeout(updateTimer, 1000);
        }
      };

      updateTimer();
    }
  }
});

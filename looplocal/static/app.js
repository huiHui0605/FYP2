"use strict";
document.querySelectorAll("[data-confirm]").forEach((button) =>
  button.addEventListener("click", (event) => {
    if (!window.confirm(button.dataset.confirm)) event.preventDefault();
  }),
);
document.querySelectorAll("[data-progress]").forEach((bar) => {
  // A finite set of CSS classes keeps the stylesheet compatible with a strict CSP.
  const progress = Math.max(
    0,
    Math.min(100, Math.round(Number(bar.dataset.progress) / 5) * 5),
  );
  bar.classList.add(`progress-${progress}`);
});
document
  .getElementById("print-passport")
  ?.addEventListener("click", () => window.print());
document
  .getElementById("go-back")
  ?.addEventListener("click", () => window.history.back());
document
  .getElementById("copy-passport")
  ?.addEventListener("click", async () => {
    const status = document.getElementById("copy-status");
    try {
      await navigator.clipboard.writeText(window.location.href);
      status.textContent = "Passport link copied. Keep the story going!";
    } catch {
      status.textContent =
        "Copy the URL from your address bar to share this passport.";
    }
  });

(function () {
  "use strict";

  // Minimal custom icon set (stroke-based, matches the luxury design language).
  // Keeping this hand-rolled avoids pulling in an icon font/library.
  const ICONS = {
    wifi: '<path d="M2 8.5a15 15 0 0 1 20 0M5.5 12a10 10 0 0 1 13 0M9 15.5a5 5 0 0 1 6 0" /><circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/>',
    pool: '<path d="M3 17c1.5 1 3 1 4.5 0s3-1 4.5 0 3 1 4.5 0 3-1 4.5 0M3 12c1.5 1 3 1 4.5 0s3-1 4.5 0 3 1 4.5 0 3-1 4.5 0" /><path d="M12 3v6" />',
    parking: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M9 16V8h3.5a2.5 2.5 0 0 1 0 5H9"/>',
    spa: '<path d="M12 3c2 3 3 5 3 7a3 3 0 1 1-6 0c0-2 1-4 3-7Z"/><path d="M6 15c1 2 3 3 6 3s5-1 6-3"/>',
    gym: '<path d="M4 9v6M20 9v6M7 12h10M2 10v4M22 10v4"/>',
    bar: '<path d="M5 4h14l-6 8v7h-2v-7L5 4Z"/><path d="M9 21h6"/>',
    breakfast: '<circle cx="12" cy="13" r="7"/><path d="M9 6l1-3M12 6l0.5-3M15 6l1-3"/>',
    ac: '<rect x="3" y="6" width="18" height="6" rx="2"/><path d="M6 16v2M10 16v3M14 16v2M18 16v3"/>',
    tv: '<rect x="3" y="5" width="18" height="12" rx="2"/><path d="M9 21h6"/>',
    pet: '<circle cx="7" cy="8" r="2"/><circle cx="17" cy="8" r="2"/><circle cx="4.5" cy="13" r="1.6"/><circle cx="19.5" cy="13" r="1.6"/><path d="M12 21c-3 0-5-1.5-5-4 0-2 2-3.5 5-3.5s5 1.5 5 3.5c0 2.5-2 4-5 4Z"/>',
    view: '<circle cx="12" cy="12" r="4"/><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z"/>',
    check: '<path d="M5 13l4 4L19 7"/>',
  };

  document.querySelectorAll("[data-icon]").forEach(function (el) {
    const key = el.getAttribute("data-icon");
    const path = ICONS[key] || ICONS.check;
    el.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" width="20" height="20">${path}</svg>`;
    el.style.display = "inline-flex";
    el.style.alignItems = "center";
    el.style.justifyContent = "center";
  });
})();

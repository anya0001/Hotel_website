(function () {
  "use strict";

  // Category filter -----------------------------------------------
  const filterBar = document.querySelector("[data-gallery-filters]");
  const grid = document.querySelector("[data-gallery-grid]");

  if (filterBar && grid) {
    filterBar.querySelectorAll(".gallery-filters__btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const filter = btn.getAttribute("data-filter");
        filterBar.querySelectorAll(".gallery-filters__btn").forEach((b) => b.classList.remove("is-active"));
        btn.classList.add("is-active");

        grid.querySelectorAll(".gallery-grid__item").forEach(function (item) {
          const category = item.getAttribute("data-category");
          item.style.display = filter === "all" || category === filter ? "" : "none";
        });
      });
    });
  }

  // Lightbox -----------------------------------------------
  const lightbox = document.getElementById("lightbox");
  const lightboxImage = document.getElementById("lightboxImage");
  const lightboxClose = document.getElementById("lightboxClose");

  document.querySelectorAll(".gallery-grid__item img[data-full]").forEach(function (img) {
    img.style.cursor = "zoom-in";
    img.addEventListener("click", function () {
      if (!lightbox || !lightboxImage) return;
      lightboxImage.src = img.getAttribute("data-full");
      lightboxImage.alt = img.alt;
      lightbox.hidden = false;
    });
  });

  if (lightboxClose) {
    lightboxClose.addEventListener("click", () => (lightbox.hidden = true));
  }
  if (lightbox) {
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) lightbox.hidden = true;
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") lightbox.hidden = true;
    });
  }
})();

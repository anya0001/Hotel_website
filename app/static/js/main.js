(function () {
  "use strict";

  // Mobile nav toggle -----------------------------------------------
  const navToggle = document.getElementById("navToggle");
  const siteNav = document.getElementById("site-nav");

  if (navToggle && siteNav) {
    navToggle.addEventListener("click", function () {
      const isOpen = siteNav.classList.toggle("is-open");
      navToggle.classList.toggle("is-open", isOpen);
      navToggle.setAttribute("aria-expanded", String(isOpen));
    });
  }

  // User account dropdown -----------------------------------------------
  const userMenuTrigger = document.getElementById("userMenuTrigger");
  const userMenuDropdown = document.getElementById("userMenuDropdown");

  if (userMenuTrigger && userMenuDropdown) {
    userMenuTrigger.addEventListener("click", function (e) {
      e.stopPropagation();
      const isOpen = userMenuDropdown.classList.toggle("is-open");
      userMenuTrigger.setAttribute("aria-expanded", String(isOpen));
    });

    document.addEventListener("click", function (e) {
      if (!userMenuDropdown.contains(e.target) && !userMenuTrigger.contains(e.target)) {
        userMenuDropdown.classList.remove("is-open");
        userMenuTrigger.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Flash message dismiss + auto-hide -----------------------------------------------
  document.querySelectorAll(".flash-message").forEach(function (msg) {
    const closeBtn = msg.querySelector(".flash-message__close");
    const dismiss = () => {
      msg.style.opacity = "0";
      msg.style.transform = "translateY(-8px)";
      setTimeout(() => msg.remove(), 200);
    };
    if (closeBtn) closeBtn.addEventListener("click", dismiss);
    setTimeout(dismiss, 6000);
  });

  // Accordion (FAQ) -----------------------------------------------
  document.querySelectorAll("[data-accordion]").forEach(function (accordion) {
    accordion.querySelectorAll(".accordion__trigger").forEach(function (trigger) {
      trigger.addEventListener("click", function () {
        const item = trigger.closest(".accordion__item");
        const wasOpen = item.classList.contains("is-open");
        accordion.querySelectorAll(".accordion__item").forEach((i) => i.classList.remove("is-open"));
        if (!wasOpen) item.classList.add("is-open");
      });
    });
  });

  // Sticky header shrink shadow on scroll -----------------------------------------------
  const header = document.getElementById("site-header");
  if (header) {
    window.addEventListener("scroll", function () {
      header.classList.toggle("is-scrolled", window.scrollY > 12);
    }, { passive: true });
  }

  // Ensure check-out date input never precedes check-in -----------------------------------------------
  document.querySelectorAll('input[name="check_in"]').forEach(function (checkInInput) {
    const form = checkInInput.closest("form");
    if (!form) return;
    const checkOutInput = form.querySelector('input[name="check_out"]');
    if (!checkOutInput) return;
    checkInInput.addEventListener("change", function () {
      if (checkInInput.value) {
        checkOutInput.min = checkInInput.value;
        if (checkOutInput.value && checkOutInput.value <= checkInInput.value) {
          checkOutInput.value = "";
        }
      }
    });
  });
})();

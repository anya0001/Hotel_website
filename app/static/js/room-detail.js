(function () {
  "use strict";

  // Gallery thumbnail switching -----------------------------------------------
  const mainImage = document.getElementById("galleryMainImage");
  document.querySelectorAll(".room-gallery__thumb").forEach(function (thumb) {
    thumb.addEventListener("click", function () {
      if (!mainImage) return;
      mainImage.src = thumb.getAttribute("data-full");
      document.querySelectorAll(".room-gallery__thumb").forEach((t) => t.classList.remove("is-active"));
      thumb.classList.add("is-active");
    });
  });

  // Live price estimate on the booking panel -----------------------------------------------
  const bookingPanel = document.getElementById("bookingPanel");
  if (bookingPanel) {
    const roomId = bookingPanel.getAttribute("data-room-id");
    const pricePerNight = parseFloat(bookingPanel.getAttribute("data-price"));
    const checkInInput = bookingPanel.querySelector("#bp_check_in");
    const checkOutInput = bookingPanel.querySelector("#bp_check_out");
    const estimateEl = document.getElementById("bookingEstimate");

    function updateEstimate() {
      if (!checkInInput.value || !checkOutInput.value || !estimateEl) return;
      const checkIn = new Date(checkInInput.value);
      const checkOut = new Date(checkOutInput.value);
      const nights = Math.round((checkOut - checkIn) / (1000 * 60 * 60 * 24));

      if (nights <= 0) {
        estimateEl.textContent = "";
        return;
      }

      const total = (nights * pricePerNight).toFixed(2);
      estimateEl.textContent = `${nights} night${nights > 1 ? "s" : ""} \u00d7 $${pricePerNight.toFixed(2)} = $${total} total`;

      // Confirm live availability without blocking submission.
      fetch(`/api/rooms/${roomId}/availability?check_in=${checkInInput.value}&check_out=${checkOutInput.value}`)
        .then((r) => r.json())
        .then((data) => {
          if (data && data.available === false) {
            estimateEl.textContent = "Not available for these dates — please choose different ones.";
          }
        })
        .catch(() => {});
    }

    [checkInInput, checkOutInput].forEach((input) => {
      if (input) input.addEventListener("change", updateEstimate);
    });
  }

  // Availability calendar (90-day view) -----------------------------------------------
  const calendarEl = document.getElementById("availabilityCalendar");
  if (calendarEl) {
    const roomId = calendarEl.getAttribute("data-room-id");
    fetch(`/api/rooms/${roomId}/calendar`)
      .then((r) => r.json())
      .then((data) => {
        calendarEl.innerHTML = "";
        data.days.slice(0, 28).forEach(function (day) {
          const cell = document.createElement("div");
          const date = new Date(day.date);
          cell.className = "availability-calendar__day";
          if (day.sold_out) {
            cell.classList.add("is-sold-out");
          } else if (day.available_units <= Math.max(1, Math.round(data.total_units * 0.25))) {
            cell.classList.add("is-limited");
          }
          cell.textContent = date.getDate();
          cell.title = day.sold_out ? "Sold out" : `${day.available_units} available`;
          calendarEl.appendChild(cell);
        });
      })
      .catch(() => {
        calendarEl.innerHTML = '<p class="availability-calendar__hint">Availability could not be loaded. Please contact us to check dates.</p>';
      });
  }
})();

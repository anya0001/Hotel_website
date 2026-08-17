(function () {
  "use strict";

  const canvas = document.getElementById("revenueChart");
  if (canvas && typeof Chart !== "undefined") {
    const labels = JSON.parse(canvas.getAttribute("data-labels") || "[]");
    const values = JSON.parse(canvas.getAttribute("data-values") || "[]");

    new Chart(canvas, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [{
          label: "Revenue",
          data: values,
          backgroundColor: "#0A4D68",
          borderRadius: 6,
          maxBarThickness: 48,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            ticks: { callback: (val) => "$" + val.toLocaleString() },
          },
        },
      },
    });
  }

  document.querySelectorAll("[data-admin-search-form]").forEach((form) => {
    const input = form.querySelector("input[type='search']");
    const clearButton = form.querySelector("[data-search-clear]");
    const table = document.getElementById(form.dataset.searchTable);
    if (!input || !table) return;

    const rows = Array.from(table.querySelectorAll("tbody tr"));

    const filterRows = () => {
      const term = input.value.trim().toLowerCase();
      let visible = 0;

      rows.forEach((row) => {
        const matches = !term || row.textContent.toLowerCase().includes(term);
        row.hidden = !matches;
        if (matches) visible += 1;
      });

      if (clearButton) clearButton.hidden = !term;
      table.dataset.searchVisible = String(visible);
    };

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      filterRows();
    });

    input.addEventListener("input", filterRows);

    clearButton?.addEventListener("click", () => {
      input.value = "";
      filterRows();
      input.focus();
    });
  });
})();

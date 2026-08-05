(function () {
  "use strict";

  const canvas = document.getElementById("revenueChart");
  if (!canvas || typeof Chart === "undefined") return;

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
})();

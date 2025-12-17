// static/js/result.js

document.addEventListener("DOMContentLoaded", function () {
  // =======================
  // グラフ描画
  // =======================
  if (window.resultChartData) {
    const labels = window.resultChartData.labels || [];
    const scores = window.resultChartData.scores || [];

    const canvas = document.getElementById("chart");
    if (canvas && typeof Chart !== "undefined") {
      new Chart(canvas, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [{
            label: "平均スコア",
            data: scores,
            backgroundColor: "rgba(54, 162, 235, 0.6)"
          }]
        },
        options: {
          scales: {
            y: {
              beginAtZero: true,
              max: 100
            }
          }
        }
      });
    }
  }

  // =======================
  // おすすめパネルの開閉
  // =======================
  const wrapper = document.getElementById("recommend-wrapper");
  if (!wrapper) return;

  const toggleBtn = document.getElementById("recommend-toggle");
  const closeBtn  = document.getElementById("recommend-close");

  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      wrapper.classList.toggle("open");
    });
  }

  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      wrapper.classList.remove("open");
    });
  }
});

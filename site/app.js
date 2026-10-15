// Phase 6: read data.json and draw the dashboard.
// Order follows the brief: answer -> volume -> pipeline -> conversion -> revenue -> cleaning.

const BLUE = "#2a78d6";

// colors for the 8 stages: blues = in progress, green = won, greys = dropped out
const STAGE_COLORS = {
  "Qualified Opt In": "#86b6ef",
  "Booked call": "#2a78d6",
  "Follow Up": "#104281",
  "Closed": "#0ca30c",
  "Disqualified": "#d6d5cf",
  "Cancelled": "#b5b3ab",
  "No Show": "#959389",
  "Lost": "#76746d",
};

const fmt = new Intl.NumberFormat("en-US");
const money = (n) => "$" + fmt.format(Math.round(n));
const pct = (n) => (n === null ? "—" : Math.round(n * 100) + "%");

// small helper: create an element with text (textContent is safe - never innerHTML with data)
function el(tag, text, className) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (className) e.className = className;
  return e;
}

// shared look for every Chart.js chart
Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', sans-serif";
Chart.defaults.color = "#5f5e5a";
Chart.defaults.plugins.legend.display = false;

// 1. load the numbers, then draw everything
fetch("data.json")
  .then((response) => response.json())
  .then(draw)
  .catch(() => {
    document.getElementById("updated").textContent = "Could not load data.json";
  });

function draw(data) {
  const sources = data.sources;
  const P = data.by_source;

  document.getElementById("updated").textContent =
    "Data updated " + new Date(data.updated).toLocaleString("en-GB",
      { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });

  drawAnswer(data.advice);
  drawScorecard(sources, P, data.advice);
  drawVolume(sources, P);
  drawPipeline(sources, P, data.stages);
  drawFunnels(sources, P, data.funnel_steps);
  drawConversionTable(sources, P, data.funnel_steps);
  drawRevenue(sources, P);
  drawCleaning(data.cleaning, data.checks);
}

// ---------------------------------------------------------------- the answer
function drawAnswer(advice) {
  document.getElementById("headline").textContent = advice.headline;
  document.getElementById("subline").textContent = advice.subline;
  document.getElementById("caution").textContent = advice.caution;
}

// ---------------------------------------------------------------- scorecard table
function drawScorecard(sources, P, advice) {
  const table = document.getElementById("scorecard");
  const head = el("tr");
  ["Source", "Leads", "Entered pipeline", "Won", "Win rate", "Revenue", "Average sale", "Revenue per lead"]
    .forEach((h) => head.append(el("th", h)));
  table.append(head);

  const sorted = [...sources].sort((a, b) => P[b].revenue_per_lead - P[a].revenue_per_lead);
  sorted.forEach((s) => {
    const p = P[s];
    const row = el("tr");
    const name = el("td", s);
    if (s === advice.best) name.append(el("span", "grow", "tag"));
    if (s === advice.worst) name.append(el("span", "cut back", "tag cut"));
    if (p.small_sample) name.append(el("span", "few leads", "tag"));
    row.append(name);
    [fmt.format(p.leads), fmt.format(p.deals), fmt.format(p.won), pct(p.win_rate),
     money(p.revenue), p.avg_sale ? money(p.avg_sale) : "—", money(p.revenue_per_lead)]
      .forEach((v) => row.append(el("td", v)));
    table.append(row);
  });
}

// ---------------------------------------------------------------- 1. volume (bar chart)
function drawVolume(sources, P) {
  new Chart(document.getElementById("volumeChart"), {
    type: "bar",
    data: {
      labels: sources,
      datasets: [{ data: sources.map((s) => P[s].leads), backgroundColor: BLUE, borderRadius: 4, maxBarThickness: 22 }],
    },
    options: {
      indexAxis: "y",                // horizontal bars: long source names stay readable
      maintainAspectRatio: false,
      scales: { x: { beginAtZero: true, title: { display: true, text: "Leads" } }, y: { grid: { display: false } } },
      plugins: { tooltip: { callbacks: { label: (c) => `${c.raw} leads` } } },
    },
  });
}

// ---------------------------------------------------------------- 2. pipeline (stacked bar)
function drawPipeline(sources, P, stages) {
  new Chart(document.getElementById("pipelineChart"), {
    type: "bar",
    data: {
      labels: sources,
      // one dataset per stage; stacking puts them end to end in each source's bar
      datasets: stages.map((stage) => ({
        label: stage,
        data: sources.map((s) => P[s].stages[stage]),
        backgroundColor: STAGE_COLORS[stage],
        borderColor: "#ffffff",
        borderWidth: 1,
        maxBarThickness: 24,
      })),
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      scales: {
        x: { stacked: true, beginAtZero: true, title: { display: true, text: "Deals" } },
        y: { stacked: true, grid: { display: false } },
      },
      plugins: {
        legend: { display: true, position: "bottom", labels: { boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: (c) => {
              const total = P[c.label].deals;
              return `${c.dataset.label}: ${c.raw} of ${total} deals (${pct(c.raw / total)})`;
            },
          },
        },
      },
    },
  });
}

// ---------------------------------------------------------------- 3. funnels (plain HTML)
function drawFunnels(sources, P, steps) {
  const box = document.getElementById("funnels");
  sources.forEach((s) => {
    const p = P[s];
    const f = el("div", undefined, "funnel");
    f.append(el("h4", s));
    p.reached.forEach((n, i) => {
      if (i > 0) f.append(el("div", "↓ " + pct(p.conversion[i - 1]), "rate"));
      const row = el("div", undefined, "step");
      const barBox = el("div", undefined, "bar-box");
      const bar = el("div", undefined, i === steps.length - 1 ? "bar won" : "bar");
      bar.style.width = (p.reached[0] ? (n / p.reached[0]) * 100 : 0) + "%";
      bar.title = `${n} people reached "${steps[i]}"`;
      barBox.append(bar);
      row.append(el("span", steps[i]), barBox, el("span", fmt.format(n), "n"));
      f.append(row);
    });
    box.append(f);
  });
}

function drawConversionTable(sources, P, steps) {
  const table = document.getElementById("conversionTable");
  const head = el("tr");
  head.append(el("th", "Source"));
  for (let i = 1; i < steps.length; i++) head.append(el("th", `${steps[i - 1]} → ${steps[i]}`));
  head.append(el("th", "Lead → sale"));
  table.append(head);

  // the best value in each column gets a star
  const columns = steps.length;   // 4 step columns + 1 overall column
  const best = [];
  for (let i = 0; i < columns; i++) {
    const values = sources.map((s) => (i < columns - 1 ? P[s].conversion[i] : P[s].win_rate)).filter((v) => v !== null);
    best.push(Math.max(...values));
  }
  sources.forEach((s) => {
    const row = el("tr");
    row.append(el("td", s));
    for (let i = 0; i < columns; i++) {
      const v = i < columns - 1 ? P[s].conversion[i] : P[s].win_rate;
      const isBest = v !== null && v === best[i];
      row.append(el("td", (isBest ? "★ " : "") + pct(v), isBest ? "best" : undefined));
    }
    table.append(row);
  });
}

// ---------------------------------------------------------------- 4. revenue (sorted bar)
function drawRevenue(sources, P) {
  const sorted = [...sources].sort((a, b) => P[b].revenue - P[a].revenue);
  new Chart(document.getElementById("revenueChart"), {
    type: "bar",
    data: {
      labels: sorted,
      datasets: [{ data: sorted.map((s) => P[s].revenue), backgroundColor: BLUE, borderRadius: 4, maxBarThickness: 22 }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      scales: {
        x: { beginAtZero: true, ticks: { callback: (v) => "$" + fmt.format(v / 1000) + "k" },
             title: { display: true, text: "Revenue from won deals" } },
        y: { grid: { display: false } },
      },
      plugins: { tooltip: { callbacks: { label: (c) => `${money(c.raw)} from ${P[c.label].won} sales` } } },
    },
  });
}

// ---------------------------------------------------------------- cleaning + checks
function drawCleaning(cleaning, checks) {
  const s = cleaning.start, e = cleaning.end;
  const boxes = document.getElementById("cleanBoxes");
  [[`${s.leads} leads · ${s.deals} deals`, "Pulled from GoHighLevel"],
   [`${s.leads - e.leads} leads · ${s.deals - e.deals} deals`, "Removed (reasons below)"],
   [`${e.leads} leads · ${e.deals} deals`, "Counted in this dashboard"]].forEach(([big, small]) => {
    const b = el("div", undefined, "box");
    b.append(el("b", big), el("span", small, "muted"));
    boxes.append(b);
  });

  const logBox = document.getElementById("cleanLog");
  [["removed", "Removed"], ["flagged", "Kept, but handled with care"]].forEach(([kind, title]) => {
    const items = cleaning.log.filter((x) => x.kind === kind && (x.leads || x.deals));
    if (!items.length) return;
    logBox.append(el("div", title, "group"));
    items.forEach((x) => {
      const item = el("div", undefined, "log-item");
      const text = el("div");
      text.append(el("strong", x.title), el("p", x.why));
      const count = [x.leads ? `${x.leads} leads` : "", x.deals ? `${x.deals} deals` : ""].filter(Boolean).join(" · ");
      item.append(text, el("div", count, "count"));
      logBox.append(item);
    });
  });

  const list = document.getElementById("checks");
  checks.forEach((c) => list.append(el("li", (c.passed ? "✓ " : "✗ ") + c.check)));
}
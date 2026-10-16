// Phase 6: read data.json and draw the dashboard.
// Order follows the brief: answer -> volume -> pipeline -> conversion -> revenue -> cleaning.

const BLUE = "#2a78d6";

// one color per channel group (blue / orange / aqua: checked to stay distinguishable for colour-blind readers)
const GROUP_COLORS = {
  "Paid ads": "#2a78d6",
  "Outbound": "#eb6834",
  "Organic": "#1baf7a",
  "Unclassified": "#a9a79f",
};

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

// must match the schedule in .github/workflows/refresh.yml ("17 * * * *" = every hour at :17 UTC)
const REFRESH_MINUTE_UTC = 17;
const STALE_AFTER_HOURS = 3;   // older than this means the hourly update has probably stopped

const FONT = "Onest, system-ui, -apple-system, 'Segoe UI', sans-serif";
const INK = "#13232f";
const MUTED = "#5a6b79";

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

// a small colored square + the group name (used in legends and table headings)
function swatch(color) {
  const i = el("i", undefined, "swatch");
  i.style.background = color;
  return i;
}

// legend for the group colors, placed just above a chart
function groupLegend(canvasId, groups) {
  const legend = el("div", undefined, "group-legend");
  groups.forEach((g) => {
    const item = el("span");
    item.append(swatch(GROUP_COLORS[g.name]), g.name);
    legend.append(item);
  });
  const chartBox = document.getElementById(canvasId).parentElement;
  chartBox.before(legend);
}

// a full-width heading row inside a table, e.g. "Paid ads - bought with ad budget"
function groupRow(group, columns) {
  const row = el("tr", undefined, "group-row");
  const cell = el("td");
  cell.colSpan = columns;
  cell.append(swatch(GROUP_COLORS[group.name]), el("strong", group.name), el("span", group.note, "muted-inline"));
  row.append(cell);
  return row;
}

// prints each bar's value just past its end, so nobody has to hover (phones can't hover)
const barValueLabels = {
  id: "barValueLabels",
  afterDatasetsDraw(chart, args, options) {
    const { ctx } = chart;
    ctx.save();
    ctx.font = `600 12px ${FONT}`;
    ctx.fillStyle = INK;
    ctx.textBaseline = "middle";
    chart.getDatasetMeta(0).data.forEach((bar, i) => {
      ctx.fillText(options.format(chart.data.datasets[0].data[i]), bar.x + 6, bar.y);
    });
    ctx.restore();
  },
};

// shared look for every Chart.js chart
Chart.defaults.font.family = FONT;
Chart.defaults.font.size = 13;
Chart.defaults.color = MUTED;
Chart.defaults.plugins.legend.display = false;

// 1. load the numbers, then draw everything
fetch(`data.json?t=${Date.now()}`, { cache: "no-store" })   // ?t= skips old cached copies
  .then((response) => response.json())
  .then((data) => document.fonts.ready.then(() => draw(data)))   // wait for the web font so charts use it
  .catch(() => {
    document.getElementById("updated").textContent = "Could not load data.json";
  });

function draw(data) {
  const sources = data.sources;
  const P = data.by_source;

  drawStatus(data.updated);

  drawAnswer(data.advice);
  drawBoard(data.advice, P);
  drawInsights(sources, P, data.funnel_steps);
  highlightRail();
  const groups = data.groups;
  drawScorecard(sources, P, data.advice, groups);
  drawVolume(sources, P, groups);
  drawPipeline(sources, P, data.stages);
  drawFunnels(sources, P, data.funnel_steps, groups);
  drawConversionTable(sources, P, data.funnel_steps, groups);
  drawRevenue(sources, P, groups);
  drawCleaning(data.cleaning, data.checks);
}

// ---------------------------------------------------------------- status: last update, countdown, check button
function nextRefresh(now) {
  const next = new Date(now);
  next.setUTCMinutes(REFRESH_MINUTE_UTC, 0, 0);
  if (next <= now) next.setUTCHours(next.getUTCHours() + 1);
  return next;
}

function countdownText() {
  const mins = Math.max(1, Math.ceil((nextRefresh(new Date()) - new Date()) / 60000));
  return `Next update from GoHighLevel in about ${mins} min`;
}

function drawStatus(updated) {
  const when = new Date(updated);
  document.getElementById("updated").textContent = "Numbers updated " + when.toLocaleString("en-GB",
    { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

  const next = document.getElementById("next");
  const tick = () => { next.textContent = countdownText(); };
  tick();
  setInterval(tick, 30000);   // update the countdown every 30 seconds

  // warn if the automatic update seems to have stopped
  const hoursOld = (Date.now() - when) / 3600000;
  if (hoursOld > STALE_AFTER_HOURS) {
    const stale = document.getElementById("stale");
    stale.textContent = `These numbers are ${Math.floor(hoursOld)} hours old. They normally update every hour, ` +
      "so the automatic update may have stopped. Ask whoever manages this dashboard to check it.";
    stale.hidden = false;
  }

  // "Check for new numbers": looks for a newer data.json and reloads the page if there is one
  const button = document.getElementById("refreshBtn");
  const msg = document.getElementById("refreshMsg");
  button.addEventListener("click", async () => {
    button.disabled = true;
    msg.textContent = "Checking…";
    try {
      const fresh = await (await fetch(`data.json?t=${Date.now()}`, { cache: "no-store" })).json();
      if (new Date(fresh.updated) > when) {
        msg.textContent = "New numbers found. Reloading…";
        location.reload();
        return;
      }
      msg.textContent = "You're already seeing the latest numbers.";
    } catch (e) {
      msg.textContent = "Couldn't check right now. Try again in a minute.";
    }
    button.disabled = false;
  });
}

// ---------------------------------------------------------------- the answer
function drawAnswer(advice) {
  document.getElementById("headline").textContent = advice.headline;
  document.getElementById("subline").textContent = advice.subline;
  document.getElementById("caution").textContent = advice.caution;
}

// ---------------------------------------------------------------- decision board: paid channels, ranked
function drawBoard(advice, P) {
  const board = document.getElementById("board");
  const paid = advice.ranked.filter((s) => P[s].group === "Paid ads");
  const max = Math.max(...paid.map((s) => P[s].revenue_per_lead), 1);
  paid.forEach((s) => {
    const p = P[s];
    const [cls, word] = (s === advice.best || s === advice.tied_best) ? ["grow", "Grow"]
      : (s === advice.worst || s === advice.tied_worst) ? ["cut", "Cut back"] : ["hold", "Hold"];
    const row = el("div", undefined, "board-row");
    const name = el("div", undefined, "board-name");
    name.append(s, el("span", word, "verdict " + cls));
    const bar = el("div", undefined, "board-bar");
    const fill = el("span");
    fill.style.width = (p.revenue_per_lead / max) * 100 + "%";
    bar.append(fill);
    const sales = `${p.won} ${p.won === 1 ? "sale" : "sales"} from ${p.leads} leads, ${money(p.revenue)} revenue`;
    row.append(name, el("div", money(p.revenue_per_lead), "board-value"), bar, el("div", sales, "board-meta"));
    board.append(row);
  });
}

// ---------------------------------------------------------------- highlight tiles (each one names a single source)
function drawInsights(sources, P, steps) {
  const named = sources.filter((s) => s !== "Unknown source");
  const judged = named.filter((s) => !P[s].small_sample);
  const top = (list, key) => list.reduce((a, b) => (P[b][key] > P[a][key] ? b : a));

  const mostLeads = top(named, "leads");
  const bestRate = top(judged.length ? judged : named, "win_rate");
  const mostRevenue = top(named, "revenue");

  // the single weakest step: lowest "moved on" rate where at least 8 people were at the step above
  let leak = null;
  named.forEach((s) => P[s].conversion.forEach((r, i) => {
    if (r !== null && P[s].reached[i] >= 8 && (!leak || r < leak.r)) leak = { s, i, r };
  }));

  const tiles = [
    ["Most leads", mostLeads, `${fmt.format(P[mostLeads].leads)} leads`],
    ["Best lead-to-sale rate", bestRate, `${pct(P[bestRate].win_rate)} of its leads bought`],
    ["Most revenue", mostRevenue, `${money(P[mostRevenue].revenue)} from ${P[mostRevenue].won} sales`],
  ];
  if (leak) {
    tiles.push(["Biggest drop-off", leak.s,
      `Only ${pct(leak.r)} went from ${steps[leak.i].toLowerCase()} to ${steps[leak.i + 1].toLowerCase()}`]);
  }

  const box = document.getElementById("insights");
  tiles.forEach(([label, source, meta]) => {
    const t = el("div", undefined, "tile");
    t.append(el("p", label, "tile-label"), el("p", source, "tile-value"), el("p", meta, "tile-meta"));
    box.append(t);
  });
}

// ---------------------------------------------------------------- section rail: mark the section in view
function highlightRail() {
  const links = [...document.querySelectorAll(".rail a")];
  if (!links.length || !("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === "#" + e.target.id));
    });
  }, { rootMargin: "-30% 0px -60% 0px" });
  links.forEach((a) => {
    const target = document.querySelector(a.getAttribute("href"));
    if (target) observer.observe(target);
  });
}

// ---------------------------------------------------------------- scorecard table
function drawScorecard(sources, P, advice, groups) {
  const table = document.getElementById("scorecard");
  const head = el("tr");
  ["Source", "Leads", "Entered pipeline", "Won", "Win rate", "Revenue", "Average sale", "Revenue per lead"]
    .forEach((h) => head.append(el("th", h)));
  table.append(head);

  groups.forEach((g) => {
    table.append(groupRow(g, 8));
    const inGroup = sources.filter((s) => P[s].group === g.name)
      .sort((a, b) => P[b].revenue_per_lead - P[a].revenue_per_lead);
    inGroup.forEach((s) => addScoreRow(s));
  });

  function addScoreRow(s) {
    const p = P[s];
    const row = el("tr");
    const name = el("td", s);
    if (s === advice.best || s === advice.tied_best) name.append(el("span", "grow", "tag"));
    if (s === advice.worst || s === advice.tied_worst) name.append(el("span", "cut back", "tag cut"));
    if (p.small_sample) name.append(el("span", "few leads", "tag"));
    row.append(name);
    [fmt.format(p.leads), fmt.format(p.deals), fmt.format(p.won), pct(p.win_rate),
     money(p.revenue), p.avg_sale ? money(p.avg_sale) : "—", money(p.revenue_per_lead)]
      .forEach((v) => row.append(el("td", v)));
    table.append(row);
  }
}

// ---------------------------------------------------------------- 1. volume (bar chart)
function drawVolume(sources, P, groups) {
  groupLegend("volumeChart", groups);
  new Chart(document.getElementById("volumeChart"), {
    type: "bar",
    data: {
      labels: sources,
      datasets: [{ data: sources.map((s) => P[s].leads), backgroundColor: sources.map((s) => GROUP_COLORS[P[s].group]),
                   borderRadius: 4, maxBarThickness: 22 }],
    },
    options: {
      indexAxis: "y",                // horizontal bars: long source names stay readable
      maintainAspectRatio: false,
      layout: { padding: { right: 40 } },   // room for the number after the longest bar
      scales: { x: { beginAtZero: true, title: { display: true, text: "Leads" } }, y: { grid: { display: false } } },
      plugins: {
        tooltip: { callbacks: { label: (c) => `${c.raw} leads · ${P[c.label].group}` } },
        barValueLabels: { format: (v) => fmt.format(v) },
      },
    },
    plugins: [barValueLabels],
  });
}

// ---------------------------------------------------------------- 2. pipeline (stacked bar)
// which stages belong to which part of the journey (used for the legend)
const STAGE_GROUPS = [
  ["Still in progress", ["Qualified Opt In", "Booked call", "Follow Up"]],
  ["Won", ["Closed"]],
  ["Dropped out", ["Disqualified", "Cancelled", "No Show", "Lost"]],
];

// is a background color dark enough to need white text on it?
function isDark(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  return 0.299 * r + 0.587 * g + 0.114 * b < 150;
}

// writes the deal count inside every segment that is wide enough, and the total after each bar
const segmentLabels = {
  id: "segmentLabels",
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    const last = chart.data.datasets.length - 1;
    ctx.save();
    ctx.textBaseline = "middle";
    chart.data.datasets.forEach((ds, d) => {
      chart.getDatasetMeta(d).data.forEach((bar, i) => {
        const n = ds.data[i];
        const width = bar.x - bar.base;
        if (n > 0 && width >= 18) {                    // too-thin segments: number is in the hover instead
          ctx.font = `700 12px ${FONT}`;
          ctx.textAlign = "center";
          ctx.fillStyle = isDark(ds.backgroundColor) ? "#ffffff" : INK;
          ctx.fillText(n, bar.base + width / 2, bar.y);
        }
      });
    });
    // total at the end of each bar
    chart.getDatasetMeta(last).data.forEach((bar, i) => {
      const total = chart.data.datasets.reduce((sum, ds) => sum + ds.data[i], 0);
      ctx.font = `600 12px ${FONT}`;
      ctx.textAlign = "left";
      ctx.fillStyle = MUTED;
      ctx.fillText(`${total} deals`, bar.x + 8, bar.y);
    });
    ctx.restore();
  },
};

function drawPipeline(sources, P, stages) {
  // legend grouped by meaning, above the chart
  const legend = el("div", undefined, "stage-legend");
  STAGE_GROUPS.forEach(([title, names]) => {
    const group = el("div", undefined, "stage-legend-group");
    const items = el("div", undefined, "stage-legend-items");
    names.filter((n) => stages.includes(n)).forEach((n) => {
      const item = el("span");
      item.append(swatch(STAGE_COLORS[n]), n);
      items.append(item);
    });
    group.append(el("span", title, "stage-legend-title"), items);
    legend.append(group);
  });
  document.getElementById("pipelineChart").parentElement.before(legend);

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
        maxBarThickness: 28,
      })),
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      layout: { padding: { right: 70 } },              // room for "23 deals"
      scales: {
        x: { stacked: true, beginAtZero: true, display: false },   // numbers are written on the bars instead
        y: { stacked: true, grid: { display: false }, border: { display: false } },
      },
      plugins: {
        legend: { display: false },                     // replaced by the grouped legend above
        tooltip: {
          callbacks: {
            title: (items) => `${items[0].label} (${P[items[0].label].group})`,
            label: (c) => {
              const total = P[c.label].deals;
              return `${c.dataset.label}: ${c.raw} of ${total} deals (${pct(c.raw / total)})`;
            },
          },
        },
      },
    },
    plugins: [segmentLabels],
  });
}

// ---------------------------------------------------------------- 3. funnels (plain HTML)
// Each row: step name | bar from the left (length = people who reached it) + the count | % who moved on
function drawFunnels(sources, P, steps, groups) {
  const box = document.getElementById("funnels");
  let currentGroup = null;
  sources.forEach((s) => {
    if (P[s].group !== currentGroup) {             // sources arrive grouped, so start a new heading
      currentGroup = P[s].group;
      const g = groups.find((x) => x.name === currentGroup);
      const heading = el("div", undefined, "funnel-group");
      heading.append(swatch(GROUP_COLORS[g.name]), el("strong", g.name), el("span", g.note, "muted-inline"));
      box.append(heading);
    }
    const p = P[s];
    const f = el("div", undefined, "funnel");
    f.append(el("h4", s));

    const head = el("div", undefined, "step head");
    head.append(el("span", "Step"), el("span", "People"), el("span", "Moved on"));
    f.append(head);

    p.reached.forEach((n, i) => {
      const row = el("div", undefined, "step");
      const share = p.reached[0] ? n / p.reached[0] : 0;     // bar length vs all leads

      const track = el("div", undefined, "track");
      const bar = el("div", undefined, i === steps.length - 1 ? "bar won" : "bar");
      bar.style.width = `calc((100% - 36px) * ${share})`;   // leave room for the number
      track.append(bar, el("span", fmt.format(n), "count"));

      const rate = i === 0 ? "" : pct(p.conversion[i - 1]);  // first row has no step above
      row.title = i === 0 ? `${n} leads`
        : `${n} of ${p.reached[i - 1]} people moved on from "${steps[i - 1]}" (${rate})`;
      row.append(el("span", steps[i], "label"), track, el("span", rate, "rate"));
      f.append(row);
    });
    box.append(f);
  });
}

function drawConversionTable(sources, P, steps, groups) {
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
  let currentGroup = null;
  sources.forEach((s) => {
    if (P[s].group !== currentGroup) {
      currentGroup = P[s].group;
      table.append(groupRow(groups.find((x) => x.name === currentGroup), columns + 1));
    }
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
function drawRevenue(sources, P, groups) {
  groupLegend("revenueChart", groups);
  const sorted = [...sources].sort((a, b) => P[b].revenue - P[a].revenue);
  new Chart(document.getElementById("revenueChart"), {
    type: "bar",
    data: {
      labels: sorted,
      datasets: [{ data: sorted.map((s) => P[s].revenue), backgroundColor: sorted.map((s) => GROUP_COLORS[P[s].group]),
                   borderRadius: 4, maxBarThickness: 22 }],
    },
    options: {
      indexAxis: "y",
      maintainAspectRatio: false,
      layout: { padding: { right: 70 } },
      scales: {
        x: { beginAtZero: true, ticks: { callback: (v) => "$" + fmt.format(v / 1000) + "k" },
             title: { display: true, text: "Revenue from won deals" } },
        y: { grid: { display: false } },
      },
      plugins: {
        tooltip: { callbacks: { label: (c) => `${money(c.raw)} from ${P[c.label].won} sales · ${P[c.label].group}` } },
        barValueLabels: { format: (v) => money(v) },
      },
    },
    plugins: [barValueLabels],
  });
}

// ---------------------------------------------------------------- cleaning + checks
function drawCleaning(cleaning, checks) {
  const s = cleaning.start, e = cleaning.end;
  const boxes = document.getElementById("cleanBoxes");
  [[`${s.leads} leads, ${s.deals} deals`, "Pulled from GoHighLevel"],
   [`${s.leads - e.leads} leads, ${s.deals - e.deals} deals`, "Removed (reasons below)"],
   [`${e.leads} leads, ${e.deals} deals`, "Counted in this dashboard"]].forEach(([big, small]) => {
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
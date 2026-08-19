// Garimpo — MVP estático
// Renderização das ofertas

const SORTERS = {
  "discount-desc": (a, b) => discountRatio(b) - discountRatio(a),
  "discount-asc": (a, b) => discountRatio(a) - discountRatio(b),
  "price-desc": (a, b) => b.price - a.price,
  "price-asc": (a, b) => a.price - b.price,
};

const state = {
  products: [],
  search: "",
  sort: "discount-desc",
};

const grid = document.getElementById("deals-grid");
const emptyState = document.getElementById("empty-state");
const resultCount = document.getElementById("result-count");
const searchInput = document.getElementById("search-input");
const tabs = document.querySelectorAll(".tab");
const countdownTime = document.getElementById("countdown-time");
const countdownLabel = document.getElementById("countdown-label");

init();
startCountdown();

async function init() {
  try {
    const res = await fetch("data/products.json", { cache: "no-store" });

    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }

    const data = await res.json();

    state.products = data
      .slice()
      .sort((a, b) => new Date(b.postedAt) - new Date(a.postedAt));

    render();

  } catch (err) {
    grid.innerHTML = "";
    emptyState.hidden = false;
    emptyState.textContent =
      "Não consegui carregar as ofertas (data/products.json). Confira o console.";

    console.error("Falha ao carregar products.json:", err);
  }

  searchInput.addEventListener("input", (e) => {
    state.search = normalize(e.target.value);
    render();
  });

  tabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabs.forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");

      state.sort = btn.dataset.sort;
      render();
    });
  });
}

function render() {
  const filtered = state.products.filter((p) => {
    const haystack = normalize(`${p.title} ${p.description}`);
    return !state.search || haystack.includes(state.search);
  });

  const sorted = filtered
    .slice()
    .sort(SORTERS[state.sort] || SORTERS["discount-desc"]);

  resultCount.textContent =
    `${sorted.length} oferta${sorted.length === 1 ? "" : "s"}`;

  grid.innerHTML = "";
  emptyState.hidden = sorted.length !== 0;

  sorted.forEach((p) => {
    grid.appendChild(renderCard(p));
  });
}

// Fração de desconto (0 quando não há originalPrice ou originalPrice <= price).
// Usada tanto para ordenar quanto para o badge exibido no card.
function discountRatio(p) {
  if (p.originalPrice && p.originalPrice > p.price) {
    return 1 - p.price / p.originalPrice;
  }
  return 0;
}

function renderCard(p) {
  const card = document.createElement("article");
  card.className = "deal-card";

  const ratio = discountRatio(p);
  const discount = ratio > 0 ? Math.round(ratio * 100) : null;

  card.innerHTML = `
    <div class="deal-image-wrap">
      <img
        class="deal-thumb"
        src="${escapeHtml(p.image)}"
        alt="${escapeHtml(p.title)}"
        loading="lazy"
        onerror="this.style.display='none'; this.parentElement.classList.add('image-error')"
      />
      <span class="deal-category">
        ${p.category === "cupom" ? "CUPOM" : "OFERTA"}
      </span>
    </div>

    <div class="deal-body">

      <h2 class="deal-title">
        ${escapeHtml(p.title)}
      </h2>

      <p class="deal-desc">
        ${escapeHtml(p.description)}
      </p>

      <div class="price-area">
        <span class="price-now">
          ${formatBRL(p.price)}
        </span>

        ${
          p.originalPrice
            ? `<span class="price-was">${formatBRL(p.originalPrice)}</span>`
            : ""
        }

        ${
          discount
            ? `<span class="discount-badge">-${discount}%</span>`
            : ""
        }
      </div>

      <div class="deal-footer">

        <div class="deal-meta">
          <span class="store-badge">
            ${escapeHtml(p.store || "Amazon")}
          </span>

          <span>
            ${relativeTime(p.postedAt)}
          </span>
        </div>

        <a
          class="go-link"
          href="${escapeHtml(p.affiliateLink)}"
          target="_blank"
          rel="nofollow sponsored noopener"
        >
          Ir para Amazon
        </a>

      </div>

    </div>
  `;

  return card;
}

function formatBRL(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
  }).format(value);
}

function relativeTime(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const min = Math.floor(diffMs / 60000);

  if (min < 1) return "agora mesmo";
  if (min < 60) return `${min} min atrás`;

  const hr = Math.floor(min / 60);

  if (hr < 24) return `${hr}h atrás`;

  const days = Math.floor(hr / 24);

  return `${days}d atrás`;
}

function normalize(str) {
  return (str || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

// ============================================================
// Contador regressivo — "ofertas de hoje até 23:59"
// ============================================================
//
// Puramente visual: reseta o texto/timer à meia-noite, não altera
// os produtos exibidos.
//
// Usa fuso America/Sao_Paulo com offset fixo UTC-3, em vez de
// Intl/timeZone, porque o Brasil não adota horário de verão desde
// o Decreto 9.772/2019 — confirmado vigente também em 2026 (sexto/
// sétimo ano seguido sem ajuste sazonal). Isso evita depender do
// fuso horário do navegador do visitante, que pode estar fora do
// Brasil. Se o horário de verão for reinstituído no futuro, este
// offset fixo precisará ser revisto.
const SP_OFFSET_MS = -3 * 60 * 60 * 1000;

function getSaoPauloParts() {
  const shifted = new Date(Date.now() + SP_OFFSET_MS);

  return {
    shiftedMs: shifted.getTime(),
    year: shifted.getUTCFullYear(),
    month: shifted.getUTCMonth(),
    day: shifted.getUTCDate(),
  };
}

function startCountdown() {
  if (!countdownTime) return;

  updateCountdown();
  setInterval(updateCountdown, 1000);
}

function updateCountdown() {
  const { shiftedMs, year, month, day } = getSaoPauloParts();

  const endOfDayShifted = Date.UTC(year, month, day, 23, 59, 59, 999);
  const diff = Math.max(0, endOfDayShifted - shiftedMs);

  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor((diff % 3600000) / 60000);
  const seconds = Math.floor((diff % 60000) / 1000);

  countdownTime.textContent =
    `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;

  if (countdownLabel) {
    const dd = pad(day);
    const mm = pad(month + 1);
    const yy = String(year).slice(-2);

    countdownLabel.textContent = `Ofertas de ${dd}/${mm}/${yy} até 23:59`;
  }
}

function pad(n) {
  return String(n).padStart(2, "0");
}

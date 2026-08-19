// Garimpo — MVP estático
// Renderização das ofertas

const state = {
  products: [],
  search: "",
  filter: "all",
};

const grid = document.getElementById("deals-grid");
const emptyState = document.getElementById("empty-state");
const resultCount = document.getElementById("result-count");
const searchInput = document.getElementById("search-input");
const tabs = document.querySelectorAll(".tab");

init();

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

      state.filter = btn.dataset.filter;
      render();
    });
  });
}

function render() {
  const filtered = state.products.filter((p) => {
    const matchesFilter =
      state.filter === "all" || p.category === state.filter;

    const haystack = normalize(`${p.title} ${p.description}`);

    const matchesSearch =
      !state.search || haystack.includes(state.search);

    return matchesFilter && matchesSearch;
  });

  resultCount.textContent =
    `${filtered.length} oferta${filtered.length === 1 ? "" : "s"}`;

  grid.innerHTML = "";
  emptyState.hidden = filtered.length !== 0;

  filtered.forEach((p) => {
    grid.appendChild(renderCard(p));
  });
}

function renderCard(p) {
  const card = document.createElement("article");
  card.className = "deal-card";

  const discount =
    p.originalPrice && p.originalPrice > p.price
      ? Math.round((1 - p.price / p.originalPrice) * 100)
      : null;

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

(function () {
  const LIKES_KEY = "farmerStoreLikes";
  const PREORDER_KEY = "farmerStorePreorder";

  const parse = (key) => {
    try {
      return JSON.parse(localStorage.getItem(key) || "[]");
    } catch (_e) {
      return [];
    }
  };

  const save = (key, value) => localStorage.setItem(key, JSON.stringify(value));
  const getLikes = () => parse(LIKES_KEY);
  const getPreorders = () => parse(PREORDER_KEY);

  const setLikes = (items) => save(LIKES_KEY, items);
  const setPreorders = (items) => save(PREORDER_KEY, items);

  const upsertById = (items, product) => {
    const idx = items.findIndex((item) => item.id === product.id);
    if (idx === -1) return [...items, product];
    const clone = [...items];
    clone[idx] = { ...clone[idx], ...product };
    return clone;
  };

  const removeById = (items, id) => items.filter((item) => item.id !== id);

  const getProductFromDataset = (node) => ({
    id: Number(node.dataset.productId),
    name: node.dataset.productName,
    price: node.dataset.productPrice,
    supplier_name: node.dataset.productSupplier || "—",
    image_url: node.dataset.productImage || "",
    category_id: node.dataset.productCategoryId || "",
    is_weight_based: String(node.dataset.productIsWeightBased) === "1",
  });

  const normalizePreorderItem = (item) => ({
    ...item,
    is_weight_based: Boolean(item.is_weight_based),
    quantity: Number(item.quantity || 1),
  });

  const getAlertsContainer = () => {
    const main = document.querySelector("main.container");
    if (!main) return null;

    let holder = document.getElementById("top-alert-holder");
    if (!holder) {
      holder = document.createElement("div");
      holder.id = "top-alert-holder";
      holder.className = "d-flex flex-column gap-2 mb-3";
      main.prepend(holder);
    }
    return holder;
  };

  const showTopAlert = ({ category = "info", message, dismissible = true, actions = [] }) => {
    const holder = getAlertsContainer();
    if (!holder) return null;

    const alert = document.createElement("div");
    alert.className = `alert alert-${category} ${dismissible ? "alert-dismissible" : ""} fade show mb-0`;
    alert.role = "alert";

    const messageWrap = document.createElement("div");
    messageWrap.innerHTML = message;
    alert.appendChild(messageWrap);

    if (actions.length) {
      const row = document.createElement("div");
      row.className = "mt-2 d-flex gap-2 flex-wrap";
      actions.forEach((action) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = action.className || "btn btn-sm btn-outline-dark";
        btn.textContent = action.label;
        btn.addEventListener("click", () => action.onClick(alert));
        row.appendChild(btn);
      });
      alert.appendChild(row);
    }

    if (dismissible) {
      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "btn-close";
      closeBtn.setAttribute("data-bs-dismiss", "alert");
      closeBtn.setAttribute("aria-label", "Close");
      alert.appendChild(closeBtn);
    }

    holder.prepend(alert);
    return alert;
  };

  const isLiked = (productId) => getLikes().some((item) => item.id === Number(productId));

  const syncLikeButtons = () => {
    document.querySelectorAll("[data-like-btn]").forEach((btn) => {
      const liked = isLiked(btn.dataset.productId);
      btn.textContent = liked ? "💔 Убрать лайк" : "❤️ Лайк";
      btn.classList.toggle("btn-danger", liked);
      btn.classList.toggle("btn-outline-danger", !liked);
    });
  };

  const handleLikeToggle = (btn) => {
    const product = getProductFromDataset(btn);
    const likedNow = isLiked(product.id);

    if (!likedNow) {
      setLikes(upsertById(getLikes(), product));
      syncLikeButtons();
      showTopAlert({ category: "success", message: `Товар <strong>${product.name}</strong> добавлен в избранное.` });
      renderFavorites();
      return;
    }

    setLikes(removeById(getLikes(), product.id));
    syncLikeButtons();
    renderFavorites();

    showTopAlert({
      category: "warning",
      message: `Лайк для <strong>${product.name}</strong> снят.`,
      actions: [
        {
          label: "Отменить",
          className: "btn btn-sm btn-dark",
          onClick: (alertNode) => {
            setLikes(upsertById(getLikes(), product));
            syncLikeButtons();
            renderFavorites();
            if (alertNode) alertNode.remove();
          }
        }
      ]
    });
  };

  const handlePreorderToggle = (btn) => {
    const product = getProductFromDataset(btn);
    const exists = getPreorders().some((item) => item.id === product.id);
    if (!exists) {
      setPreorders(upsertById(getPreorders(), { ...product, quantity: product.is_weight_based ? 0.5 : 1 }));
      showTopAlert({ category: "primary", message: `Товар <strong>${product.name}</strong> добавлен в предзаказ.` });
    } else {
      setPreorders(removeById(getPreorders(), product.id));
      showTopAlert({ category: "secondary", message: `Товар <strong>${product.name}</strong> удалён из предзаказа.` });
    }
    renderPreorders();
  };

  const renderFavorites = () => {
    const holder = document.getElementById("favoritesList");
    if (!holder) return;

    const likes = getLikes();
    if (!likes.length) {
      holder.innerHTML = '<div class="alert alert-light border mb-0">Пока нет лайкнутых товаров.</div>';
      return;
    }

    holder.innerHTML = likes.map((item) => `
      <div class="card mb-3 shadow-sm">
        <div class="row g-0">
          <div class="col-md-3">
            <img src="${item.image_url || 'https://placehold.co/400x250?text=Product'}" class="img-fluid rounded-start h-100" style="object-fit:cover;" alt="${item.name}">
          </div>
          <div class="col-md-9">
            <div class="card-body d-flex justify-content-between gap-3 align-items-start">
              <div>
                <h5 class="card-title mb-1">${item.name}</h5>
                <p class="mb-1 text-muted">Поставщик: ${item.supplier_name}</p>
                <p class="mb-0 fw-semibold">${item.price} ₽</p>
              </div>
              <div class="d-flex flex-column gap-2">
                <button type="button" class="btn btn-sm btn-danger" data-like-btn
                  data-product-id="${item.id}"
                  data-product-name="${item.name}"
                  data-product-price="${item.price}"
                  data-product-supplier="${item.supplier_name}"
                  data-product-image="${item.image_url}"
                  data-product-category-id="${item.category_id}"
                  data-product-is-weight-based="${item.is_weight_based ? 1 : 0}">💔 Убрать лайк</button>
                <button type="button" class="btn btn-sm btn-outline-primary" data-preorder-btn
                  data-product-id="${item.id}"
                  data-product-name="${item.name}"
                  data-product-price="${item.price}"
                  data-product-supplier="${item.supplier_name}"
                  data-product-image="${item.image_url}"
                  data-product-category-id="${item.category_id}"
                  data-product-is-weight-based="${item.is_weight_based ? 1 : 0}">🛒 В предзаказ</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    `).join("");
  };

  const renderPreorders = () => {
    const holder = document.getElementById("preorderList");
    if (!holder) return;

    const items = getPreorders().map(normalizePreorderItem);
    if (!items.length) {
      holder.innerHTML = '<div class="alert alert-light border mb-0">Список предзаказа пуст.</div>';
      return;
    }

    holder.innerHTML = items.map((item) => {
      const step = item.is_weight_based ? "0.1" : "1";
      const min = item.is_weight_based ? "0.1" : "1";
      const suffix = item.is_weight_based ? "кг (ориентировочно)" : "упак.";
      return `
      <div class="card mb-2 shadow-sm">
        <div class="card-body d-flex justify-content-between align-items-center gap-3">
          <div>
            <div class="fw-semibold">${item.name}</div>
            <div class="text-muted small">${item.supplier_name}</div>
          </div>
          <div class="d-flex align-items-center gap-2">
            <input type="number" class="form-control form-control-sm" style="width: 120px" min="${min}" step="${step}" value="${item.quantity}" data-preorder-qty data-product-id="${item.id}">
            <span class="small text-muted">${suffix}</span>
          </div>
        </div>
      </div>`;
    }).join("");
  };

  const initPreorderConfirm = () => {
    const confirmBtn = document.getElementById("confirmPreorderBtn");
    if (!confirmBtn) return;

    confirmBtn.addEventListener("click", async () => {
      const items = getPreorders().map(normalizePreorderItem);
      if (!items.length) {
        showTopAlert({ category: "warning", message: "Добавьте товары в предзаказ перед подтверждением." });
        return;
      }

      const time = document.getElementById("preorderTime")?.value || "";
      const comment = document.getElementById("preorderComment")?.value || "";

      const resp = await fetch("/preorder/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items, time, comment })
      });

      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        showTopAlert({ category: "danger", message: data.error || "Не удалось оформить предзаказ" });
        return;
      }

      setPreorders([]);
      renderPreorders();
      showTopAlert({ category: "success", message: "Предзаказ оформлен! Мы скоро свяжемся с вами." });
    });
  };

  document.addEventListener("change", (event) => {
    const qtyInput = event.target.closest("[data-preorder-qty]");
    if (!qtyInput) return;

    const productId = Number(qtyInput.dataset.productId);
    const items = getPreorders().map(normalizePreorderItem);
    const idx = items.findIndex((item) => item.id === productId);
    if (idx === -1) return;

    let value = Number(qtyInput.value || 0);
    const min = items[idx].is_weight_based ? 0.1 : 1;

    if (!Number.isFinite(value) || value < min) {
      value = min;
    }

    items[idx].quantity = value;
    setPreorders(items);
    renderPreorders();
  });

  document.addEventListener("click", (event) => {
    const likeBtn = event.target.closest("[data-like-btn]");
    if (likeBtn) {
      handleLikeToggle(likeBtn);
      return;
    }

    const preorderBtn = event.target.closest("[data-preorder-btn]");
    if (preorderBtn) {
      handlePreorderToggle(preorderBtn);
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    renderFavorites();
    renderPreorders();
    syncLikeButtons();
    initPreorderConfirm();
  });
})();

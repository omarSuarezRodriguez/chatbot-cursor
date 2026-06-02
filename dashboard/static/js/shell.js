(function () {
  "use strict";

  var sidebar = document.getElementById("app-sidebar");
  var backdrop = document.getElementById("sidebar-backdrop");
  var menuBtn = document.getElementById("sidebar-toggle");

  if (sidebar && menuBtn) {
    function openSidebar() {
      sidebar.classList.add("is-open");
      if (backdrop) {
        backdrop.classList.add("is-visible");
        backdrop.setAttribute("aria-hidden", "false");
      }
      menuBtn.setAttribute("aria-expanded", "true");
    }

    function closeSidebar() {
      sidebar.classList.remove("is-open");
      if (backdrop) {
        backdrop.classList.remove("is-visible");
        backdrop.setAttribute("aria-hidden", "true");
      }
      menuBtn.setAttribute("aria-expanded", "false");
    }

    function toggleSidebar() {
      if (sidebar.classList.contains("is-open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    }

    menuBtn.addEventListener("click", toggleSidebar);

    if (backdrop) {
      backdrop.addEventListener("click", closeSidebar);
    }

    sidebar.querySelectorAll(".app-nav-link").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.matchMedia("(max-width: 768px)").matches) {
          closeSidebar();
        }
      });
    });

    window.addEventListener("resize", function () {
      if (window.matchMedia("(min-width: 769px)").matches) {
        closeSidebar();
      }
    });
  }

  document.querySelectorAll("tr[data-row-href]").forEach(function (row) {
    row.classList.add("is-clickable");
    row.addEventListener("click", function (e) {
      if (e.target.closest("a, button, form, .action-menu, input, select, textarea, label")) {
        return;
      }
      var href = row.getAttribute("data-row-href");
      if (href) {
        window.location.href = href;
      }
    });
  });

  function closeAllActionMenus() {
    document.querySelectorAll(".action-menu.is-open").forEach(function (menu) {
      menu.classList.remove("is-open");
      var btn = menu.querySelector(".action-menu__trigger");
      if (btn) {
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  document.querySelectorAll("[data-action-menu]").forEach(function (menu) {
    var trigger = menu.querySelector(".action-menu__trigger");
    var panel = menu.querySelector(".action-menu__panel");
    if (!trigger || !panel) {
      return;
    }

    trigger.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = menu.classList.contains("is-open");
      closeAllActionMenus();
      if (!isOpen) {
        menu.classList.add("is-open");
        trigger.setAttribute("aria-expanded", "true");
      }
    });

    panel.addEventListener("click", function (e) {
      e.stopPropagation();
    });
  });

  document.addEventListener("click", closeAllActionMenus);

  var confirmEl = null;
  var pendingSubmit = null;

  function ensureConfirmDialog() {
    if (confirmEl) {
      return confirmEl;
    }
    confirmEl = document.createElement("div");
    confirmEl.className = "confirm-dialog";
    confirmEl.setAttribute("role", "alertdialog");
    confirmEl.setAttribute("aria-modal", "true");
    confirmEl.setAttribute("aria-hidden", "true");
    confirmEl.innerHTML =
      '<div class="confirm-dialog__box">' +
      '<p class="confirm-dialog__title" id="confirm-dialog-title">¿Confirmar?</p>' +
      '<p class="confirm-dialog__message" id="confirm-dialog-message"></p>' +
      '<div class="confirm-dialog__actions">' +
      '<button type="button" class="btn btn-ghost" data-confirm-cancel>Cancelar</button>' +
      '<button type="button" class="btn btn-primary" data-confirm-ok>Confirmar</button>' +
      "</div></div>";
    document.body.appendChild(confirmEl);

    confirmEl.querySelector("[data-confirm-cancel]").addEventListener("click", closeConfirmDialog);
    confirmEl.querySelector("[data-confirm-ok]").addEventListener("click", function () {
      if (pendingSubmit) {
        pendingSubmit();
      }
      closeConfirmDialog();
    });
    confirmEl.addEventListener("click", function (e) {
      if (e.target === confirmEl) {
        closeConfirmDialog();
      }
    });
    return confirmEl;
  }

  function openConfirmDialog(message, onConfirm) {
    var dlg = ensureConfirmDialog();
    pendingSubmit = onConfirm;
    dlg.querySelector("#confirm-dialog-message").textContent = message;
    dlg.classList.add("is-open");
    dlg.setAttribute("aria-hidden", "false");
    dlg.querySelector("[data-confirm-ok]").focus();
  }

  function closeConfirmDialog() {
    if (confirmEl) {
      confirmEl.classList.remove("is-open");
      confirmEl.setAttribute("aria-hidden", "true");
    }
    pendingSubmit = null;
  }

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeAllActionMenus();
      closeConfirmDialog();
    }
  });

  function bindConfirm(form, message) {
    form.addEventListener("submit", function (e) {
      if (form.dataset.confirmed === "1") {
        form.dataset.confirmed = "";
        return;
      }
      e.preventDefault();
      openConfirmDialog(message, function () {
        form.dataset.confirmed = "1";
        form.submit();
      });
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    bindConfirm(form, form.getAttribute("data-confirm") || "¿Continuar?");
  });

  // Menu workspace: quick filters for large catalogs
  var menuSearchInput = document.getElementById("menu-search");
  if (menuSearchInput) {
    var categoryFilter = document.querySelector("[data-menu-category-filter]");
    var statusFilter = document.querySelector("[data-menu-status-filter]");
    var visibleProductsEl = document.querySelector("[data-menu-visible-products]");
    var totalProductsEl = document.querySelector("[data-menu-total-products]");
    var menuCategories = Array.prototype.slice.call(
      document.querySelectorAll("[data-menu-category]")
    );
    var allMenuRows = Array.prototype.slice.call(
      document.querySelectorAll("[data-menu-item]")
    );

    if (totalProductsEl) {
      totalProductsEl.textContent = String(allMenuRows.length);
    }

    function normalize(str) {
      return (str || "").toLowerCase();
    }

    function matchesItem(row, query) {
      if (!query) {
        return true;
      }
      var name = normalize(row.getAttribute("data-menu-item-name"));
      var category = normalize(row.getAttribute("data-menu-item-category"));
      var id = normalize(row.getAttribute("data-menu-item-id"));
      return (
        name.indexOf(query) !== -1 ||
        category.indexOf(query) !== -1 ||
        (id && id.indexOf(query) !== -1)
      );
    }

    function applyMenuSearch(query) {
      var trimmed = query.trim().toLowerCase();
      var selectedCategory = categoryFilter ? normalize(categoryFilter.value) : "";
      var selectedStatus = statusFilter ? normalize(statusFilter.value) : "";
      var visibleProducts = 0;

      menuCategories.forEach(function (categoryEl) {
        var categoryName = normalize(
          categoryEl.getAttribute("data-menu-category-name")
        );
        var categoryCountEl = categoryEl.querySelector("[data-menu-category-count]");
        var rows = Array.prototype.slice.call(
          categoryEl.querySelectorAll("[data-menu-item]")
        );
        var visibleInCategory = 0;
        rows.forEach(function (row) {
          var rowAvailable = row.getAttribute("data-menu-item-available") === "1";
          var passesText = matchesItem(row, trimmed);
          var passesCategory = !selectedCategory || categoryName === selectedCategory;
          var passesStatus =
            !selectedStatus ||
            (selectedStatus === "available" && rowAvailable) ||
            (selectedStatus === "unavailable" && !rowAvailable);
          var show = passesText && passesCategory && passesStatus;

          row.style.display = show ? "" : "none";
          if (show) {
            visibleInCategory += 1;
            visibleProducts += 1;
          }
        });
        if (categoryCountEl) {
          categoryCountEl.textContent = String(visibleInCategory);
        }
        categoryEl.style.display = visibleInCategory > 0 ? "" : "none";
      });

      if (visibleProductsEl) {
        visibleProductsEl.textContent = String(visibleProducts);
      }
    }

    menuSearchInput.addEventListener("input", function (e) {
      applyMenuSearch(e.target.value || "");
    });
    if (categoryFilter) {
      categoryFilter.addEventListener("change", function () {
        applyMenuSearch(menuSearchInput.value || "");
      });
    }
    if (statusFilter) {
      statusFilter.addEventListener("change", function () {
        applyMenuSearch(menuSearchInput.value || "");
      });
    }

    document.querySelectorAll("[data-menu-jump]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var categoryName = normalize(btn.getAttribute("data-menu-jump"));
        if (categoryFilter) {
          categoryFilter.value = categoryName;
        }
        applyMenuSearch(menuSearchInput.value || "");
        var target = document.querySelector(
          '[data-menu-category-anchor="' + categoryName + '"]'
        );
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });

    applyMenuSearch("");
  }
})();

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

  function bindClickableRows(root) {
    (root || document).querySelectorAll("tr[data-row-href]").forEach(function (row) {
      if (row.dataset.rowNavBound === "1") {
        return;
      }
      row.dataset.rowNavBound = "1";
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
  }

  function closeAllActionMenus() {
    document.querySelectorAll(".action-menu.is-open").forEach(function (menu) {
      menu.classList.remove("is-open");
      var btn = menu.querySelector(".action-menu__trigger");
      if (btn) {
        btn.setAttribute("aria-expanded", "false");
      }
    });
  }

  function bindActionMenus(root) {
    (root || document).querySelectorAll("[data-action-menu]").forEach(function (menu) {
      if (menu.dataset.actionMenuBound === "1") {
        return;
      }
      menu.dataset.actionMenuBound = "1";
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
  }

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
    if (form.dataset.confirmBound === "1") {
      return;
    }
    form.dataset.confirmBound = "1";
    form.addEventListener("submit", function (e) {
      if (form.dataset.submitting === "1") {
        e.preventDefault();
        return;
      }
      if (form.dataset.confirmed === "1") {
        form.dataset.confirmed = "";
        form.dataset.submitting = "1";
        return;
      }
      e.preventDefault();
      openConfirmDialog(message, function () {
        if (form.dataset.submitting === "1") {
          return;
        }
        form.dataset.confirmed = "1";
        form.dataset.submitting = "1";
        var submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
          if (!submitBtn.dataset.originalLabel) {
            submitBtn.dataset.originalLabel = submitBtn.textContent;
          }
          submitBtn.disabled = true;
          submitBtn.textContent = submitBtn.getAttribute("data-submit-label") || "Procesando...";
        }
        if (form.dataset.asyncConfirm === "1") {
          submitAsyncConfirm(form);
          return;
        }
        form.submit();
      });
    });
  }

  function removeRowAndMaybeEmpty(form) {
    var row = form.closest("tr[data-row-href]");
    if (row) {
      row.remove();
    }
    var remaining = document.querySelectorAll("tr[data-row-href]").length;
    if (remaining === 0) {
      window.location.reload();
    }
  }

  function submitAsyncConfirm(form) {
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (res) {
        if (!res.ok) {
          throw new Error("confirm_failed");
        }
        removeRowAndMaybeEmpty(form);
      })
      .catch(function () {
        // Fallback to normal navigation if async request fails.
        form.dataset.asyncConfirm = "";
        form.submit();
      });
  }

  function bindConfirmForms(root) {
    (root || document).querySelectorAll("form[data-confirm]").forEach(function (form) {
      bindConfirm(form, form.getAttribute("data-confirm") || "¿Continuar?");
    });
  }

  function bindInteractiveUI(root) {
    bindClickableRows(root);
    bindActionMenus(root);
    bindConfirmForms(root);
  }

  bindInteractiveUI(document);

  // Orders list auto-refresh (fail-soft): poll current URL every 5s and only patch orders section.
  (function initOrdersPolling() {
    var tabs = document.querySelector(".status-tabs");
    if (!tabs) {
      return;
    }

    function orderKeyFromRow(row) {
      var id = row.getAttribute("data-order-id");
      var status = (row.getAttribute("data-order-status") || "").toLowerCase();
      if (!id) {
        var href = row.getAttribute("data-row-href") || "";
        var parts = href.split("/").filter(Boolean);
        id = parts.length ? parts[parts.length - 1] : "";
      }
      return id + ":" + status;
    }

    function getVersionFromDocument(doc) {
      var keys = [];
      var rows = doc.querySelectorAll("tr[data-row-href]");
      rows.forEach(function (row) {
        var key = orderKeyFromRow(row);
        if (key) keys.push(key);
      });
      keys.sort();
      return keys.join("|") + "|" + rows.length;
    }

    function replaceOrRemove(currentEl, nextEl) {
      if (currentEl && nextEl) {
        currentEl.replaceWith(nextEl);
        return;
      }
      if (currentEl && !nextEl) {
        currentEl.remove();
      }
    }

    function updateOrdersSection(nextDoc) {
      var nextTableWrap = nextDoc.querySelector(".table-wrap.card");
      var nextPagination = nextDoc.querySelector("nav.pagination");
      var nextWaiting = nextDoc.querySelector(".empty-state--orders-waiting");
      var nextEmpty = nextDoc.querySelector(
        ".empty-state.card:not(.empty-state--orders-waiting)"
      );
      var currentTableWrap = document.querySelector(".table-wrap.card");
      var currentPagination = document.querySelector("nav.pagination");
      var currentWaiting = document.querySelector(".empty-state--orders-waiting");
      var currentEmpty = document.querySelector(
        ".empty-state.card:not(.empty-state--orders-waiting)"
      );
      var anchor = document.querySelector(".status-tabs.card");
      var toolbar = document.querySelector(".data-toolbar.card");
      var insertAfter = toolbar || anchor;

      replaceOrRemove(currentTableWrap, nextTableWrap);
      replaceOrRemove(currentPagination, nextPagination);
      replaceOrRemove(currentWaiting, nextWaiting);
      replaceOrRemove(currentEmpty, nextEmpty);

      if (insertAfter) {
        if (!document.querySelector(".table-wrap.card") && nextTableWrap) {
          insertAfter.insertAdjacentElement("afterend", nextTableWrap);
        }
        if (!document.querySelector("nav.pagination") && nextPagination) {
          var tableWrap = document.querySelector(".table-wrap.card");
          (tableWrap || insertAfter).insertAdjacentElement("afterend", nextPagination);
        }
        if (!document.querySelector(".empty-state--orders-waiting") && nextWaiting) {
          insertAfter.insertAdjacentElement("afterend", nextWaiting);
        }
        if (
          !document.querySelector(".empty-state.card:not(.empty-state--orders-waiting)") &&
          nextEmpty
        ) {
          insertAfter.insertAdjacentElement("afterend", nextEmpty);
        }
      }

      bindInteractiveUI(document);
    }

    var currentVersion = getVersionFromDocument(document);
    setInterval(function () {
      if (document.hidden) {
        return;
      }
      var pollUrl = new URL(window.location.href);
      pollUrl.searchParams.set("_poll", String(Date.now()));
      fetch(pollUrl.toString(), {
        method: "GET",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
        cache: "no-store",
      })
        .then(function (res) {
          if (!res.ok) {
            throw new Error("poll_failed");
          }
          return res.text();
        })
        .then(function (html) {
          var nextDoc = new DOMParser().parseFromString(html, "text/html");
          var nextVersion = getVersionFromDocument(nextDoc);
          if (nextVersion === currentVersion) {
            return;
          }
          updateOrdersSection(nextDoc);
          currentVersion = nextVersion;
        })
        .catch(function () {
          // fail-soft: keep current UI and retry in next cycle
        });
    }, 5000);
  })();

  // Menu workspace: quick filters for large catalogs
  var menuSearchInput = document.getElementById("menu-search");
  if (menuSearchInput) {
    var categoryFilter = document.querySelector("[data-menu-category-filter]");
    var totalProductsEl = document.querySelector("[data-menu-total-products]");
    var allMenuRows = Array.prototype.slice.call(
      document.querySelectorAll("[data-menu-item]")
    );
    var emptyStateEl = document.querySelector("[data-menu-empty]");

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

    function applyMenuFilters(query) {
      var trimmed = query.trim().toLowerCase();
      var selectedCategory = categoryFilter ? normalize(categoryFilter.value) : "";
      var visibleProducts = 0;

      allMenuRows.forEach(function (row) {
        var rowCategory = normalize(row.getAttribute("data-menu-item-category"));
        var passesText = matchesItem(row, trimmed);
        var passesCategory = !selectedCategory || rowCategory === selectedCategory;
        var show = passesText && passesCategory;

        row.style.display = show ? "" : "none";
        if (show) {
          visibleProducts += 1;
        }
      });

      if (emptyStateEl) {
        emptyStateEl.style.display = visibleProducts > 0 ? "none" : "";
      }
    }

    menuSearchInput.addEventListener("input", function (e) {
      applyMenuFilters(e.target.value || "");
    });
    if (categoryFilter) {
      categoryFilter.addEventListener("change", function () {
        applyMenuFilters(menuSearchInput.value || "");
      });
    }

    document.querySelectorAll("[data-menu-select]").forEach(function (button) {
      button.addEventListener("click", function () {
        var card = button.closest("[data-menu-item]");
        if (!card) {
          return;
        }
        var isSelected = card.classList.toggle("is-selected");
        button.setAttribute("aria-pressed", isSelected ? "true" : "false");
        button.textContent = isSelected ? "Seleccionado" : "Seleccionar";
      });
    });

    applyMenuFilters("");
  }
})();

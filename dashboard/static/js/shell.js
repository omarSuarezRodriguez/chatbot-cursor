(function () {
  "use strict";

  var sidebar = document.getElementById("app-sidebar");
  var backdrop = document.getElementById("sidebar-backdrop");
  var menuBtn = document.getElementById("sidebar-toggle");

  if (!sidebar || !menuBtn) {
    return;
  }

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
})();

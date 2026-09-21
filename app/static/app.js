/* InvoiceCraft — vanilla JS micro-interactions. No frameworks, no requests. */
(() => {
  "use strict";

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* ---------- Toasts ---------- */
  const TOAST_TTL = 4500;

  function toastContainer() {
    let box = document.getElementById("toasts");
    if (!box) {
      box = document.createElement("div");
      box.className = "toasts";
      box.id = "toasts";
      box.setAttribute("aria-live", "polite");
      document.body.appendChild(box);
    }
    return box;
  }

  function dismissToast(el) {
    if (!el || el.classList.contains("toast-exit")) return;
    el.classList.add("toast-exit");
    setTimeout(() => el.remove(), reducedMotion.matches ? 0 : 280);
  }

  function armToast(el) {
    el.addEventListener("click", () => dismissToast(el));
    setTimeout(() => dismissToast(el), TOAST_TTL);
  }

  window.toast = function toast(message, kind = "success") {
    const el = document.createElement("div");
    el.className = `toast toast-${kind}`;
    el.setAttribute("role", "status");
    el.textContent = message;
    toastContainer().appendChild(el);
    armToast(el);
    return el;
  };

  // Server-rendered flashes: slide in via CSS, auto-dismiss, click-to-dismiss.
  document.querySelectorAll("#toasts .toast").forEach(armToast);

  /* ---------- Copy to clipboard: [data-copy] ---------- */
  document.addEventListener("click", (event) => {
    const el = event.target.closest("[data-copy]");
    if (!el) return;
    event.preventDefault();
    const text = el.dataset.copy;
    const fallback = () => window.prompt("Copy to clipboard:", text);
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(() => window.toast("Copied to clipboard"))
        .catch(fallback);
    } else {
      fallback();
    }
  });

  /* ---------- Mobile nav: [data-nav-toggle] ---------- */
  const navToggle = document.querySelector("[data-nav-toggle]");
  if (navToggle) {
    navToggle.addEventListener("click", () => {
      const header = navToggle.closest(".topnav");
      if (!header) return;
      const open = header.classList.toggle("nav-open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
  }

  /* ---------- Scroll reveal: .reveal → .in ---------- */
  if (!reducedMotion.matches && "IntersectionObserver" in window) {
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add("in");
            io.unobserve(entry.target);
          }
        }
      },
      { threshold: 0.12 }
    );
    document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  }
})();

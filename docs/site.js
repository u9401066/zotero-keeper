(() => {
  "use strict";

  const menuButton = document.querySelector(".menu-toggle");
  const menu = document.querySelector("#site-menu");
  const navigationLinks = [...document.querySelectorAll(".main-nav a[href^='#']")];

  const setMenu = (open) => {
    if (!menuButton || !menu) return;
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "關閉導覽選單" : "開啟導覽選單");
    menu.dataset.open = String(open);
  };

  menuButton?.addEventListener("click", () => {
    setMenu(menuButton.getAttribute("aria-expanded") !== "true");
  });

  menu?.addEventListener("click", (event) => {
    if (!(event.target instanceof HTMLAnchorElement)) return;

    const target = event.target.hash ? document.querySelector(event.target.hash) : null;
    window.setTimeout(() => {
      setMenu(false);
      if (!(target instanceof HTMLElement)) return;
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      target.addEventListener("blur", () => target.removeAttribute("tabindex"), { once: true });
    }, 0);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setMenu(false);
      menuButton?.focus();
    }
  });

  const sectionLinks = navigationLinks
    .map((link) => ({ link, section: document.querySelector(link.hash) }))
    .filter(({ section }) => section instanceof HTMLElement);

  if ("IntersectionObserver" in window && sectionLinks.length) {
    const visibleSections = new Map();
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          visibleSections.set(entry.target.id, entry.isIntersecting ? entry.intersectionRatio : 0);
        }

        const current = [...visibleSections.entries()]
          .filter(([, ratio]) => ratio > 0)
          .sort((a, b) => b[1] - a[1])[0]?.[0];

        for (const { link, section } of sectionLinks) {
          if (section.id === current) link.setAttribute("aria-current", "true");
          else link.removeAttribute("aria-current");
        }
      },
      { rootMargin: "-18% 0px -58%", threshold: [0.12, 0.35, 0.65] },
    );

    for (const { section } of sectionLinks) observer.observe(section);
  }

  window.addEventListener("resize", () => {
    if (window.innerWidth > 780) setMenu(false);
  });
})();

(function () {
  const root = document.documentElement;
  const toggleBtn = document.querySelector(".theme-toggle");

  // Initialise from localStorage or system preference
  const storedTheme = window.localStorage.getItem("theme");
  const prefersDark = window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  if (storedTheme === "light" || storedTheme === "dark") {
    root.setAttribute("data-theme", storedTheme);
  } else if (prefersDark) {
    root.setAttribute("data-theme", "dark");
  } else {
    root.setAttribute("data-theme", "light");
  }

  function updateToggleLabel(theme) {
    if (!toggleBtn) return;
    if (theme === "light") {
      toggleBtn.textContent = "🌙 Dark";
    } else {
      toggleBtn.textContent = "☀️ Light";
    }
  }

  const currentTheme = root.getAttribute("data-theme") || "dark";
  updateToggleLabel(currentTheme);

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const current = root.getAttribute("data-theme") === "light" ? "light" : "dark";
      const next = current === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      window.localStorage.setItem("theme", next);
      updateToggleLabel(next);
    });
  }
})();

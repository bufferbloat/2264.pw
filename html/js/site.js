(function () {
    const reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    function randomBetween(min, max) {
        return Math.random() * (max - min) + min;
    }

    function getStarCount() {
        if (reducedMotionQuery.matches) {
            return 0;
        }

        if (window.innerWidth < 520) {
            return 60;
        }

        if (window.innerWidth < 900) {
            return 90;
        }

        return 130;
    }

    function createStar() {
        const star = document.createElement("div");
        star.className = "star";
        star.style.setProperty("--star-x", `${randomBetween(0, 100)}%`);
        star.style.setProperty("--star-y", `${randomBetween(0, 100)}%`);
        star.style.setProperty("--star-dx", `${randomBetween(-70, 70)}px`);
        star.style.setProperty("--star-dy", `${randomBetween(-70, 70)}px`);
        star.style.setProperty("--star-duration", `${randomBetween(4, 8)}s`);
        star.style.setProperty("--star-delay", `${randomBetween(-8, 0)}s`);
        return star;
    }

    function initStars() {
        const container = document.querySelector(".stars");
        if (!container) {
            return;
        }

        let currentCount = -1;

        function renderStars() {
            const nextCount = getStarCount();
            if (nextCount === currentCount) {
                return;
            }

            currentCount = nextCount;
            container.replaceChildren();

            const fragment = document.createDocumentFragment();
            for (let i = 0; i < nextCount; i += 1) {
                fragment.appendChild(createStar());
            }
            container.appendChild(fragment);
        }

        let resizeTimer = 0;
        window.addEventListener("resize", function () {
            window.clearTimeout(resizeTimer);
            resizeTimer = window.setTimeout(renderStars, 150);
        });

        reducedMotionQuery.addEventListener("change", renderStars);
        renderStars();
    }

    function initBackgroundToggle() {
        const toggle = document.getElementById("bgToggle");

        function setPressedState() {
            if (toggle) {
                toggle.setAttribute("aria-pressed", document.body.classList.contains("bg-nebula") ? "true" : "false");
            }
        }

        function toggleBackground() {
            document.body.classList.toggle("bg-nebula");
            setPressedState();
        }

        if (toggle) {
            toggle.addEventListener("click", toggleBackground);
            setPressedState();
        }

        document.body.addEventListener("dblclick", function (event) {
            if (event.target === document.body) {
                toggleBackground();
            }
        });
    }

    function normalizePath(path) {
        const normalized = path
            .replace(/\/index\.html$/, "/")
            .replace(/\.html$/, "")
            .replace(/\/+$/, "");
        return normalized || "/";
    }

    function initCurrentNavigation() {
        const currentPath = normalizePath(window.location.pathname);
        const currentLink = Array.from(document.querySelectorAll(".site-nav a"))
            .map((link) => ({ link, path: normalizePath(new URL(link.href).pathname) }))
            .filter(({ path }) => currentPath === path || (path !== "/" && currentPath.startsWith(`${path}/`)))
            .sort((first, second) => second.path.length - first.path.length)[0];

        if (currentLink) {
            currentLink.link.setAttribute("aria-current", "page");
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        initStars();
        initBackgroundToggle();
        initCurrentNavigation();
    });
})();

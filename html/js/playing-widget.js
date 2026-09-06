(() => {
const PLAYING_URL = "/api/playing";
const POLL_INTERVAL_MS = 15_000;

let currentActivity = null;
let elapsedInterval = null;
let marqueeCleanup = null;

function getWidget() {
    return document.getElementById("playing");
}

function setIdleState(isIdle) {
    getWidget()?.closest(".widget-playing")?.classList.toggle("is-idle", isIdle);
}

function clearElapsedTimer() {
    if (elapsedInterval !== null) {
        clearInterval(elapsedInterval);
        elapsedInterval = null;
    }
}

function clearMarquee() {
    marqueeCleanup?.();
    marqueeCleanup = null;
}

function initializeMarquee(viewport, text) {
    let frame = null;

    const updateMarquee = () => {
        frame = null;
        viewport.classList.remove("is-marquee");
        viewport.style.removeProperty("--marquee-offset");
        viewport.style.removeProperty("--marquee-duration");

        const overflowDistance = Math.ceil(text.scrollWidth - viewport.clientWidth);
        if (overflowDistance <= 1) {
            return;
        }

        const travelSeconds = Math.max(4, overflowDistance / 18);
        viewport.style.setProperty("--marquee-offset", `-${overflowDistance}px`);
        viewport.style.setProperty("--marquee-duration", `${(travelSeconds + 2).toFixed(2)}s`);
        void viewport.offsetWidth;
        viewport.classList.add("is-marquee");
    };

    const scheduleUpdate = () => {
        if (frame !== null) {
            cancelAnimationFrame(frame);
        }
        frame = requestAnimationFrame(updateMarquee);
    };

    const observer = new ResizeObserver(scheduleUpdate);
    observer.observe(viewport);
    scheduleUpdate();

    document.fonts?.ready.then(() => {
        if (viewport.isConnected) {
            scheduleUpdate();
        }
    });

    marqueeCleanup = () => {
        observer.disconnect();
        if (frame !== null) {
            cancelAnimationFrame(frame);
        }
    };
}

function formatElapsed(startedAt) {
    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - startedAt.getTime()) / 1000));
    const hours = Math.floor(elapsedSeconds / 3600);
    const minutes = Math.floor((elapsedSeconds % 3600) / 60);
    const seconds = elapsedSeconds % 60;

    if (hours > 0) {
        return `for ${hours}h ${String(minutes).padStart(2, "0")}m`;
    }

    return `for ${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

function renderNothing() {
    clearElapsedTimer();
    clearMarquee();
    currentActivity = null;
    setIdleState(true);

    const widget = getWidget();
    if (!widget) {
        return;
    }

    const title = document.createElement("p");
    title.className = "playing-title";
    title.textContent = "playing";

    const nothing = document.createElement("p");
    nothing.className = "playing-nothing";
    nothing.textContent = "Nothing";

    widget.replaceChildren(title, nothing);
}

function renderPlaying(activity) {
    clearElapsedTimer();
    clearMarquee();
    currentActivity = activity;
    setIdleState(false);

    const widget = getWidget();
    if (!widget) {
        return;
    }

    const title = document.createElement("p");
    title.className = "playing-title";
    title.textContent = "playing";

    const content = document.createElement("div");
    content.className = "playing-content";

    if (activity.imageUrl) {
        const artwork = document.createElement("img");
        artwork.className = "playing-art";
        artwork.src = activity.imageUrl;
        artwork.alt = `${activity.name} artwork`;
        artwork.loading = "lazy";
        artwork.addEventListener("error", () => {
            artwork.replaceWith(createArtworkPlaceholder());
        }, { once: true });
        content.append(artwork);
    } else {
        content.append(createArtworkPlaceholder());
    }

    const info = document.createElement("div");
    info.className = "playing-info";

    const name = document.createElement("p");
    name.className = "playing-name marquee-viewport";
    name.title = activity.name;

    const nameText = document.createElement("span");
    nameText.className = "marquee-text";
    nameText.textContent = activity.name;
    name.append(nameText);
    info.append(name);

    const startedAt = activity.startedAt ? new Date(activity.startedAt) : null;
    if (startedAt && !Number.isNaN(startedAt.getTime())) {
        const elapsed = document.createElement("p");
        elapsed.className = "playing-elapsed";
        const updateElapsed = () => {
            elapsed.textContent = formatElapsed(startedAt);
        };
        updateElapsed();
        elapsedInterval = setInterval(updateElapsed, 1000);
        info.append(elapsed);
    }

    content.append(info);
    widget.replaceChildren(title, content);
    initializeMarquee(name, nameText);
}

function createArtworkPlaceholder() {
    const placeholder = document.createElement("div");
    placeholder.className = "playing-art-placeholder";
    placeholder.setAttribute("aria-hidden", "true");
    return placeholder;
}

function activityKey(activity) {
    return JSON.stringify([activity.active, activity.name, activity.imageUrl, activity.startedAt]);
}

async function loadPlaying() {
    try {
        const response = await fetch(PLAYING_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Playing request failed with ${response.status}`);
        }

        const activity = await response.json();
        if (!activity.active || typeof activity.name !== "string") {
            renderNothing();
            return;
        }

        if (!currentActivity || activityKey(activity) !== activityKey(currentActivity)) {
            renderPlaying(activity);
        }
    } catch (error) {
        renderNothing();
    }
}

loadPlaying();
setInterval(loadPlaying, POLL_INTERVAL_MS);
})();

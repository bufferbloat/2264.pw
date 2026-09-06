(function () {
    function formatCount(count) {
        if (count < 1000) {
            return String(count);
        }

        const units = [
            { value: 1000000000, suffix: "b" },
            { value: 1000000, suffix: "m" },
            { value: 1000, suffix: "k" }
        ];
        const unit = units.find(function (candidate) {
            return count >= candidate.value;
        });
        const scaled = count / unit.value;
        const rounded = scaled < 10
            ? Math.round(scaled * 10) / 10
            : Math.round(scaled);
        return `${rounded}${unit.suffix}`;
    }

    function isValidCount(value) {
        return Number.isSafeInteger(value) && value >= 0;
    }

    function initializePostStats() {
        const post = document.querySelector(".post-container[data-post-slug]");
        const stats = post && post.querySelector(".post-stats");
        const viewDisplay = stats && stats.querySelector(".post-views");
        const viewCount = viewDisplay && viewDisplay.querySelector("[data-view-count]");
        const likeButton = stats && stats.querySelector(".post-like");
        const likeCount = likeButton && likeButton.querySelector("[data-like-count]");

        if (!post || !stats || !viewDisplay || !viewCount || !likeButton || !likeCount) {
            return;
        }

        const slug = post.dataset.postSlug;
        let liked = false;

        function render(result) {
            const views = Number(result.views);
            const likes = Number(result.likes);
            if (!isValidCount(views) || !isValidCount(likes) || typeof result.liked !== "boolean") {
                return false;
            }

            liked = result.liked;
            const viewLabel = `${views.toLocaleString("en-US")} ${views === 1 ? "view" : "views"}`;
            const likeLabel = `${likes.toLocaleString("en-US")} ${likes === 1 ? "like" : "likes"}`;

            viewCount.textContent = formatCount(views);
            viewDisplay.title = viewLabel;
            viewDisplay.setAttribute("aria-label", viewLabel);

            likeCount.textContent = formatCount(likes);
            likeButton.setAttribute("aria-pressed", String(liked));
            likeButton.setAttribute("aria-label", `${liked ? "Unlike" : "Like"} this post. ${likeLabel}`);
            likeButton.title = `${liked ? "Unlike" : "Like"} this post · ${likeLabel}`;

            stats.hidden = false;
            return true;
        }

        likeButton.addEventListener("click", async function () {
            if (likeButton.disabled) {
                return;
            }

            likeButton.disabled = true;
            try {
                const response = await fetch(`/api/blog/posts/${encodeURIComponent(slug)}/like`, {
                    method: liked ? "DELETE" : "PUT",
                    credentials: "same-origin",
                    cache: "no-store",
                    headers: {
                        "Accept": "application/json",
                        "X-Blog-Like": "1"
                    }
                });

                if (response.ok) {
                    render(await response.json());
                }
            } catch (_) {
                // Leave the current state intact if the request fails.
            } finally {
                likeButton.disabled = false;
            }
        });

        fetch(`/api/blog/posts/${encodeURIComponent(slug)}/view`, {
            method: "POST",
            credentials: "same-origin",
            cache: "no-store",
            headers: {
                "Accept": "application/json",
                "X-Blog-View": "1"
            }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Post statistics unavailable");
                }
                return response.json();
            })
            .then(render)
            .catch(function () {
                // Keep the statistics hidden when the service is unavailable.
            });
    }

    function initializeBlogCardStats() {
        const cards = Array.from(document.querySelectorAll(".blog-post[data-post-slug]"));
        if (cards.length === 0) {
            return;
        }

        fetch("/api/blog/posts/views", {
            credentials: "same-origin",
            cache: "no-store",
            headers: { "Accept": "application/json" }
        })
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Post statistics unavailable");
                }
                return response.json();
            })
            .then(function (result) {
                if (!result.views || typeof result.views !== "object") {
                    return;
                }

                cards.forEach(function (card) {
                    const display = card.querySelector(".post-card-views");
                    const output = display && display.querySelector("[data-card-view-count]");
                    const views = Number(result.views[card.dataset.postSlug]);
                    if (!display || !output || !isValidCount(views)) {
                        return;
                    }

                    const label = `${views.toLocaleString("en-US")} ${views === 1 ? "view" : "views"}`;
                    output.textContent = formatCount(views);
                    display.title = label;
                    display.setAttribute("aria-label", label);
                    display.hidden = false;
                });
            })
            .catch(function () {
                // Keep card counters hidden when the service is unavailable.
            });
    }

    function initializeStats() {
        initializePostStats();
        initializeBlogCardStats();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeStats);
    } else {
        initializeStats();
    }
})();

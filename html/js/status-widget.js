const STATUS_URL = "https://status.cafe/users/way/status.json";

const title = document.querySelector(".status-title");
const username = document.getElementById("statuscafe-username");
const content = document.getElementById("statuscafe-content");

function finishLoading() {
    title.textContent = "status";
    title.classList.remove("loading-title");
}

async function loadStatus() {
    try {
        const response = await fetch(STATUS_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Status request failed with ${response.status}`);
        }

        const status = await response.json();
        if (!status.content.length) {
            content.textContent = "No status yet.";
            return;
        }

        const profile = document.createElement("a");
        profile.href = "https://status.cafe/users/way";
        profile.target = "_blank";
        profile.rel = "noopener noreferrer";
        profile.textContent = status.author;

        username.replaceChildren(
            profile,
            document.createTextNode(` ${status.face} ${status.timeAgo}`)
        );
        content.innerHTML = status.content;
    } catch (error) {
        content.textContent = "Error loading status";
    } finally {
        finishLoading();
    }
}

loadStatus();

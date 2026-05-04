// Endpoint/widget idea adapted from a MIT-licensed Nekoweb script:
// https://max.nekoweb.org/resources/license.txt
const USERNAME = "wayclient";
const BASE_URL = `https://lastfm-last-played.biancarosa.com.br/${USERNAME}/latest-song`;
const POLL_INTERVAL_MS = 30000;

let lastSuccessfulTrack = null;

function getWidget() {
    return document.getElementById("listening");
}

function replaceWidgetContent(...nodes) {
    const widget = getWidget();
    if (!widget) {
        return;
    }

    widget.replaceChildren(...nodes);
}

function createStatusLine(isPlaying) {
    const status = document.createElement("p");
    status.className = "now-playing-text";

    const dot = document.createElement("span");
    dot.className = `status-dot ${isPlaying ? "status-dot--green" : "status-dot--red"}`;

    status.append(dot, isPlaying ? "now listening" : "last listened");
    return status;
}

function renderTrack(track) {
    const isPlaying = Boolean(track["@attr"]?.nowplaying);
    const wrapper = document.createElement("div");
    wrapper.className = "content-wrapper";

    const image = document.createElement("img");
    const imageUrl = track.image?.[1]?.["#text"] || track.image?.[0]?.["#text"] || "";
    image.src = imageUrl;
    image.alt = track.album?.["#text"] ? `${track.album["#text"]} album cover` : "Album cover";
    image.loading = "lazy";

    const info = document.createElement("div");
    info.id = "trackInfo";

    const trackName = document.createElement("h3");
    trackName.id = "trackName";
    trackName.textContent = track.name || "Unknown track";

    const artistName = document.createElement("p");
    artistName.id = "artistName";
    artistName.textContent = track.artist?.["#text"] || "Unknown artist";

    info.append(trackName, artistName);
    wrapper.append(image, info);
    replaceWidgetContent(createStatusLine(isPlaying), wrapper);
}

function renderMessage(message) {
    const text = document.createElement("p");
    text.className = "widget-message";
    text.textContent = message;
    replaceWidgetContent(text);
}

async function getTrack() {
    try {
        const response = await fetch(BASE_URL, { cache: "no-store" });
        if (!response.ok) {
            throw new Error(`Last.fm request failed with ${response.status}`);
        }

        const json = await response.json();
        if (!json.track) {
            throw new Error("No track data received");
        }

        lastSuccessfulTrack = json.track;
        renderTrack(json.track);
    } catch (error) {
        if (lastSuccessfulTrack) {
            renderTrack(lastSuccessfulTrack);
            return;
        }

        renderMessage("Error loading Last.fm data");
    }
}

getTrack();
setInterval(getTrack, POLL_INTERVAL_MS);

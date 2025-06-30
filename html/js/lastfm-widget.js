// this script is under the MIT license (https://max.nekoweb.org/resources/license.txt)

const USERNAME = "wayclient";
const BASE_URL = `https://lastfm-last-played.biancarosa.com.br/${USERNAME}/latest-song`;
let lastSuccessfulTrack = null; // cache the last successful track


const updateWidgetContent = (content) => {
    const widget = document.getElementById("listening");
    if (widget) {
        widget.innerHTML = content;
    }
};

const getTrack = async () => {
    try {
        const request = await fetch(BASE_URL);
        if (!request.ok) {
            throw new Error(`HTTP error! status: ${request.status}`);
        }
        const json = await request.json();
        
        if (!json.track) {
            throw new Error('No track data received');
        }

        // cache successful response 
        lastSuccessfulTrack = json;

        let isPlaying = json.track['@attr']?.nowplaying || false;
        
        updateWidgetContent(`
        <p class="now-playing-text">${isPlaying ? 'now listening' : 'last listened'}</p>
        <div class="content-wrapper">
            <img src="${json.track.image[1]['#text']}" alt="Album cover">
            <div id="trackInfo">
                <h3 id="trackName">${json.track.name}</h3>
                <p id="artistName">${json.track.artist['#text']}</p>
            </div>
        </div>
        `);
    } catch (error) {
       
        if (lastSuccessfulTrack) {
            getTrack(); 
            return;
        }

        updateWidgetContent(`
        <div class="no-song-playing">
            <p>Error loading Last.fm data</p>
            <p style="font-size: 10px; opacity: 0.7;">${error.message}</p>
        </div>
        `);
    }
};


getTrack();

 
setInterval(getTrack, 10000); 
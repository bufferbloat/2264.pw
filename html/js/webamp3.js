import Webamp from "https://unpkg.com/webamp@2.2.0";

let webampInstance = null;
let webampLoading = false;

// AudioContext
function initializeWebamp() {
    const container = document.getElementById("webamp-container");
    if (!container || webampInstance || webampLoading) {
        return;
    }

    webampLoading = true;
    const webamp = new Webamp({
        initialSkin: {
            url: "https://cdn.webampskins.org/skins/a848e984701261b56d0e408c6ad70f9d.wsz"
        },
        initialTracks: [
            // Brothers in Arms (1985)
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "So Far Away",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/01%20So%20Far%20Away.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Money For Nothing",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/02%20Money%20For%20Nothing.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Walk Of Life",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/03%20Walk%20Of%20Life.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Your Latest Trick",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/04%20Your%20Latest%20Trick.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Why Worry",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/05%20Why%20Worry.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Ride Across The River",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/06%20Ride%20Across%20The%20River.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "The Man's Too Strong",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/07%20The%20Man's%20Too%20Strong.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "One World",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/08%20One%20World.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Brothers In Arms",
                    album: "Brothers in Arms"
                },
                url: "https://2264.pw/src/media/DireStraits/Brothers%20in%20Arms/09%20Brothers%20In%20Arms.mp3"
            },
            // Communiqué (1979)
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Once Upon a Time in the West",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/01%20Once%20Upon%20a%20Time%20in%20the%20West.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "News",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/02%20News.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Where Do You Think You're Going",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/03%20Where%20Do%20You%20Think%20You're%20Going.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Communiqué",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/04%20Communiqué.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Lady Writer",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/05%20Lady%20Writer.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Angel of Mercy",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/06%20Angel%20of%20Mercy.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Portobello Belle",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/07%20Portobello%20Belle.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Single-Handed Sailor",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/08%20Single-Handed%20Sailor.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Follow Me Home",
                    album: "Communiqué"
                },
                url: "https://2264.pw/src/media/DireStraits/Communiqué/09%20Follow%20Me%20Home.mp3"
            },
            // Dire Straits (1978) - Self-titled debut
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Down to the Waterline",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/01%20Down%20to%20the%20Waterline.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Water of Love",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/02%20Water%20of%20Love.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Setting Me Up",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/03%20Setting%20Me%20Up.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Six Blade Knife",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/04%20Six%20Blade%20Knife.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Southbound Again",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/05%20Southbound%20Again.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Sultans of Swing",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/06%20Sultans%20of%20Swing.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "In the Gallery",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/07%20In%20the%20Gallery.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Wild West End",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/08%20Wild%20West%20End.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Lions",
                    album: "Dire Straits"
                },
                url: "https://2264.pw/src/media/DireStraits/Dire%20Straits/09%20Lions.mp3"
            },
            // Love Over Gold (1982)
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Telegraph Road",
                    album: "Love Over Gold"
                },
                url: "https://2264.pw/src/media/DireStraits/Love%20Over%20Gold/01%20Telegraph%20Road.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Private Investigations",
                    album: "Love Over Gold"
                },
                url: "https://2264.pw/src/media/DireStraits/Love%20Over%20Gold/02%20Private%20Investigations.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Industrial Disease",
                    album: "Love Over Gold"
                },
                url: "https://2264.pw/src/media/DireStraits/Love%20Over%20Gold/03%20Industrial%20Disease.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Love Over Gold",
                    album: "Love Over Gold"
                },
                url: "https://2264.pw/src/media/DireStraits/Love%20Over%20Gold/04%20Love%20Over%20Gold.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "It Never Rains",
                    album: "Love Over Gold"
                },
                url: "https://2264.pw/src/media/DireStraits/Love%20Over%20Gold/05%20It%20Never%20Rains.mp3"
            },
            // Making Movies (1980)
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Tunnel Of Love",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/01%20Tunnel%20Of%20Love.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Romeo And Juliet",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/02%20Romeo%20And%20Juliet.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Skateaway",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/03%20Skateaway.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Expresso Love",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/04%20Expresso%20Love.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Hand In Hand",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/05%20Hand%20In%20Hand.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Solid Rock",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/06%20Solid%20Rock.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Les Boys",
                    album: "Making Movies"
                },
                url: "https://2264.pw/src/media/DireStraits/Making%20Movies/07%20Les%20Boys.mp3"
            },
            // On Every Street (1991)
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Calling Elvis",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/01%20Calling%20Elvis.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "On Every Street",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/02%20On%20Every%20Street.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "When It Comes to You",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/03%20When%20It%20Comes%20to%20You.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Fade to Black",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/04%20Fade%20to%20Black.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "The Bug",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/05%20The%20Bug.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "You and Your Friend",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/06%20You%20and%20Your%20Friend.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Heavy Fuel",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/07%20Heavy%20Fuel.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Iron Hand",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/08%20Iron%20Hand.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Ticket to Heaven",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/09%20Ticket%20to%20Heaven.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "My Parties",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/10%20My%20Parties.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "Planet of New Orleans",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/11%20Planet%20of%20New%20Orleans.mp3"
            },
            {
                metaData: {
                    artist: "Dire Straits",
                    title: "How Long",
                    album: "On Every Street"
                },
                url: "https://2264.pw/src/media/DireStraits/On%20Every%20Street/12%20How%20Long.mp3"
            },
            {
                metaData: {
                    artist: "XI$OW",
                    title: "HAVA NAGILA (HARDTEKK)",
                },
                url: "https://2264.pw/src/media/Others/HAVA%20NAGILA%20%28HARDTEKK%29.mp3"
            }
        ],
        availableSkins: [
            {
                url: "https://cdn.webampskins.org/skins/a848e984701261b56d0e408c6ad70f9d.wsz",
                name: "Blackamp"
            }
        ],
        enableHotkeys: true,
        enableDoubleSizeMode: false,
        enableMediaSession: true,
        zIndex: 10000,
        windowLayout: {
            main: {
                position: { top: 0, left: 0 }
            },
            equalizer: {
                position: { top: 116, left: 0 },
                closed: true
            },
            playlist: {
                position: { top: 232, left: 0 },
                size: { extraHeight: 4, extraWidth: 0 },
                closed: true
            }
        }
    });

    // Render
    webamp.renderWhenReady(container).then(() => {
        webampInstance = webamp;
        webampLoading = false;
        // AudioActivation
        document.addEventListener('click', function activateAudio() {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            if (audioContext.state === 'suspended') {
                audioContext.resume();
            }
            document.removeEventListener('click', activateAudio);
        }, { once: true });

    }).catch((error) => {
        webampLoading = false;
        console.error("Webamp failed to load:", error);
        const message = document.createElement("div");
        message.className = "widget-message";
        message.textContent = "Webamp failed to load. Please refresh the page.";
        container.replaceChildren(message);
    });
}

let typedKeys = '';

document.addEventListener('keydown', function(e) {
    if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) {
        return;
    }

    typedKeys += e.key.toLowerCase();


    if (typedKeys.length > 6) {
        typedKeys = typedKeys.slice(-6);
    }


    if (typedKeys === 'player') {
        initializeWebamp();
        typedKeys = ''; 
    }
});

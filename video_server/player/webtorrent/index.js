



function initWebtorrent(videoJson) {
    const MIN_SEEDERS = 5
    // Enable WebTorrent debugging for now.
    globalThis.localStorage.debug = '*'
    // Black pixel.
    if (videoJson['poster']) {
        console.warn("Video poster not supported in webtorrent")
    }
    //const poster = videoJson['poster'] || "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjYGBk/A8AAQkBAubzvZ0AAAAASUVORK5CYII="
    //console.log("poster: " + poster)
    const webtorrentOptions = videoJson.webtorrent
    const ICE_CONFIGURATION = {
        iceServers: [
            {
                urls: [
                    'stun:relay.socket.dev:443',
                    'stun:global.stun.twilio.com:3478'
                ]
            }
        ],
        sdpSemantics: 'unified-plan',
        bundlePolicy: 'max-bundle',
        iceCandidatePoolsize: 1
    }

    // Hack to get our torrent tracker embedded.
    // globalThis.WEBTORRENT_ANNOUNCE = [
    //  "wss://webtorrent-tracker.onrender.com"
    // ]

    const WEBTORRENT_CONFIG = {
        tracker: {
            ICE_CONFIGURATION
        }
    }

    // EXPERIMENT, does this play better with other clients?
    // const client = new WebTorrent()
    const client = new globalThis.WebTorrent(WEBTORRENT_CONFIG)
    // get the current time
    const time = new Date().getTime()

    console.log("videoJson:")
    console.log(videoJson)

    const videos = videoJson.videos

    let TORRENT_URL = null;
    let WEBSEED = null;


    // Just grab the first one for now.
    for (let i = 0; i < videos.length; i++) {
        TORRENT_URL = videos[i].torrent_url
        WEBSEED = videos[i].file_url
        break
    }

    // const options = {
    //  announce: ["wss://webtorrent-tracker.onrender.com"],
    //  getAnnounceOpts: (obj) => { console.log("getAnnounceOpts:", obj) }
    // }
    const options = undefined

    const torrent = client.add(TORRENT_URL, options, () => {
        console.log('ON TORRENT STARTED')
    })

    console.log('created torrent')

    // torrent.on('warning', console.warn)
    // torrent.on('error', console.error)
    // torrent.on('download', console.log)
    // torrent.on('upload', console.log)

    torrent.on('warning', (a) => {
        console.warn('warning:', a)
    })
    torrent.on('error', (a) => {
        console.error('error:', a)
    })
    // Spams the console.

    function throttle(func, timeFrame) {
        let lastTime = 0
        return function () {
            const now = Date.now()
            if (now - lastTime >= timeFrame) {
                func()
                lastTime = now
            }
        }
    }

    let webseedAdded = false
    let downloadedBytes = 0
    const printDownloaded = throttle(() => {
        // pretty print downloadedBytes with commas
        const prettyBytes = downloadedBytes.toLocaleString()
        console.log(`downloaded: ${prettyBytes}`)
    }, 1000)


    function addWebSeed() {
        if (!webseedAdded) {
            console.log('adding webseed')
            torrent.addWebSeed(WEBSEED)
            webseedAdded = true
        }
    }
    const $vid = document.querySelector('video')
    //$vid.poster = poster
    //$vid.setAttribute('poster', poster)
    function onVideoLoaded(videoJson) {
        console.log('onVideoLoaded')
        // console.log(document.querySelector("div.container>video"))
        // get the firsts video in the div container with the container class
        var $vid = document.querySelector("div.container>video")
        let isFirst = true
        const subtitles = videoJson.subtitles || []
        for (const subtitle of subtitles) {
            // console.log("subtitles:", subtitle);
            $sourceElement = document.createElement('track');
            // Get the current url
            const url = new URL(window.location.href);
            // Go up one directory
            let href = url.href
            href = href.replace("/index.html", "")
            if (href.endsWith("/")) {
                href = href.substring(0, href.length - 1)
            }
            // Combine the url and the subtitle file, going up one directory.
            const src = subtitle.file;
            $sourceElement.setAttribute('label', subtitle.label);
            $sourceElement.setAttribute('srclang', subtitle.srclang);
            $sourceElement.setAttribute('src', src);
            $sourceElement.setAttribute('kind', 'subtitles');
            if (isFirst) {
                $sourceElement.setAttribute('default', '');
                isFirst = false;
            }
            $vid.appendChild($sourceElement);
        }
    }
    let jobAddWebseed = setTimeout(addWebSeed, 10000)
    torrent.on('download', (a) => {
        // console.log(`download: ${a}`)
        if (downloadedBytes === 0) {
            const timeFirstByte = new Date().getTime() - time
            console.log('first byte:', timeFirstByte)
        }
        downloadedBytes += a
        printDownloaded()
        // Defer adding the webseed because we have uninterrupted download.
        clearInterval(jobAddWebseed)
        jobAddWebseed = setTimeout(addWebSeed, 5000)
    })
    // torrent.on('upload', (a) => { console.log(`upload: ${a}`) })

    torrent.on('wire', function (wire, addr) {
        console.log('connected to peer with address ', wire, addr)
        // wire.use(MyExtension)
    })

    torrent.on('noPeers', function (announceType) {
        console.log('noPeers', announceType)
    })

    torrent.on('ready', () => {

        //setInterval(() => {
        //    console.log('torrent:', torrent)
        //}, 3000)

        console.log('torrent ready')
        console.log('infoHash:', torrent.infoHash)
        const opts = { infoHash: torrent.infoHash, announce: torrent.announce }
        Tracker.scrape(opts, function (err, results) {
            try {
                const totalPeers = results.complete + results.incomplete + results.downloaded
                const threshold = 5
                if (totalPeers < MIN_SEEDERS) {
                    console.log(`Adding webseed because total number of peers ${totalPeers} is < ${threshold}`)
                    addWebSeed()
                }
            }
            catch (e) {
                console.log('scrape error:', e, "\n", err, "\n", results)
            }
        })
        // Warning! This relies on patched webtorrent ICECOMPLETE_TIMEOUT=1000
        // if aggressive
        if (webtorrentOptions.eager_webseed) {
            console.log("Adding webseed because eager mode")
            addWebSeed()
        } else {
            setTimeout(() => {
                if (downloadedBytes === 0 && !webseedAdded) {
                    console.log('Adding webseed because client choked for 7 seconds.')
                    addWebSeed()
                }
            }, 7000)

            setTimeout(() => {
                const oneMegaByte = 1024 * 512
                if (downloadedBytes < oneMegaByte && !webseedAdded) {
                    console.log('Adding webseed because client could download fast enough after 10 seconds.')
                    addWebSeed()
                }
            }, 12000)
        }

        //document.getElementById('info').innerHTML = 'Movie name: ' + torrent.name
        console.log('Torrent loaded!')
        console.log('Torrent name:', torrent.name)
        console.log('Announce list:', torrent.announce)
        console.log('Found at:', new Date().getTime() - time, ' in the load')
        console.log('Files:')
        torrent.files.forEach(file => {
            console.log('- ' + file.name)
        })
        // Torrents can contain many files. Let's use the .mp4 file
        const file = torrent.files.find(file => file.name.endsWith('.mp4') || file.name.endsWith('.webm'))
        // Display the file by adding it to the DOM
        file.renderTo('video#player', { autoplay: true })
        onVideoLoaded(videoJson)
    })
}

// Get the video.json, which will be the "d" parameter in the URL
const params = new URLSearchParams(window.location.search)
const videoJson = params.get('d')
if (!videoJson) {
    console.error('No videoJson parameter in URL')
}

fetch(videoJson, { method: 'GET' })
    .then((response) => {
        response.json().then((videoJson) => {
            console.log("videoJson:", videoJson)
            initWebtorrent(videoJson)
        })
    })
    .catch((error) => {
        console.log("error", error)
    });

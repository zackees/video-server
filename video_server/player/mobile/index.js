
function initMobileVideo(videoJson) {
    const $videoSource = document.getElementById("video-source")
    const videos = videoJson.videos;
    const video = videos[0]
    $videoSource.src = video.file_url
    // Add videoJson to the dom.
    const $vid = document.getElementById('vid1');
    $vid.setAttribute("poster", videoJson.poster)
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

    // Generate the player
    const player = videojs($vid);
    const promise = player.play()
    if (promise) {
        promise.then(() => {
            // Autoplay started
            console.log(player)
            //debugger
            // player.muted(false)
        }).catch((err) => {
            // Autoplay failed
            console.log("Autoplay failed because of ", err)
        });
    }
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
            initMobileVideo(videoJson)
        })
    })
    .catch((error) => {
        console.log("error", error)
    });


function initMobileVideo(data) {
    $videoSource = document.getElementById("video-source")
    $videoSource.src = data.mobile

    // Add data to the dom.
    const $vid = document.getElementById('vid1');
    let isFirst = true
    for (const subtitle of data.subtitles) {
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
        const baseUrl = href.substring(0, href.lastIndexOf("/"))
        // Combine the url and the subtitle file, going up one directory.
        const src = baseUrl + "/subtitles/" + subtitle.file;
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

fetch("../video.json", { method: 'GET' })
    .then((response) => {
        response.json().then((data) => {
            initMobileVideo(data)
        })
    })
    .catch((error) => {
        console.log("error", error)
    });

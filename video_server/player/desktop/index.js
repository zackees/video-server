// Get the video.json, which will be the "d" parameter in the URL
const params = new URLSearchParams(window.location.search)
const videoJson = params.get('d')
if (!videoJson) {
    console.error('No videoJson parameter in URL')
}
fetch(videoJson, { method: 'GET' })
    .then((response) => {
        response.json().then((videoJson) => {
            console.log("\nvideoJson:", videoJson)
            console.log("\n")
            const $player = document.getElementById("player");
            const videos = videoJson.videos;
            for (const video of videos) {
                const $sourceElement = document.createElement('source');
                $sourceElement.setAttribute('src', video.file_url);
                $sourceElement.setAttribute('type', 'video/mp4');
                //$sourceElement.setAttribute('size', video.height);
                $player.appendChild($sourceElement);
            }
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
                $player.appendChild($sourceElement);
            }
            // Change the second argument to your options:
            // https://github.com/sampotts/plyr/#options
            // Expose player so it can be used from the console
            globalThis.player = new Plyr('video', { captions: { active: true } });
        })
    })
    .catch((error) => {
        console.log("error", error)
    });

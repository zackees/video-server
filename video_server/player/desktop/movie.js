
(function () {
    const TIMEOUT_SHOWVIDEO = 15000 // 15 seconds until we show the video screen no matter what.
    // const videoMain = document.getElementById('video-main')
    const playBtn = document.getElementById('play-btn')
    const spinContainer = document.getElementById('spinner-container')
    const videoMain = document.getElementById('player')
    videoMain.addEventListener('pause', (event) => {
        playBtn.classList.add('active')
    })
    videoMain.addEventListener('playing', (event) => {
        playBtn.classList.remove('active')
    })
    function play() {
        const promise = videoMain.play()
        promise.then(_ => {
            // Autoplay started!
        }).catch(error => {
            // Autoplay was prevented.
            // Show a "Play" button so that user can start playback.
            console.log('Autoplay was prevented because of', error)
            playBtn.classList.add('active')
        })
    }

    playBtn.onclick = function (evt) {
        play()
        playBtn.classList.remove('active')
        evt.preventDefault()
    }

    // Autoplay the video
    spinContainer.classList.add('active')
    let jobId = null
    function oncanplay() {
        videoMain.classList.add('loaded')
        spinContainer.classList.remove('active')
        clearTimeout(jobId)
        setTimeout(() => {
            spinContainer.style.display = 'none'
        }, 2000)
        play()
    }
    videoMain.oncanplay = oncanplay
    // If it takes too long to load then show the loading screen so that users
    // understand that there's a loading problem.
    jobId = setTimeout(oncanplay, TIMEOUT_SHOWVIDEO)
    const playButtonDisableJob = setInterval(() => {
        if (!videoMain.paused) {
            playBtn.classList.remove('active')
            clearInterval(playButtonDisableJob)
        }
    })
})()

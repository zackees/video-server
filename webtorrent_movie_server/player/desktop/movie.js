
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
  function play () {
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
  function resizeSpinnerContainer () {
    let maxWidth = 0
    let maxHeight = 0
    document.querySelectorAll('.spinner').forEach(function (el) {
      const width = el.getBoundingClientRect().width
      const height = el.getBoundingClientRect().height
      maxWidth = Math.max(maxWidth, width)
      maxHeight = Math.max(maxHeight, height)
    })
    const spinnerContainer = document.getElementById('spinner-container')
    spinnerContainer.style.width = maxWidth + 'px'
    spinnerContainer.style.height = maxHeight + 'px'
  }
  resizeSpinnerContainer()
  playBtn.onclick = function (evt) {
    play()
    playBtn.classList.remove('active')
    evt.preventDefault()
  }
  function getVideoCenterPoint () {
    const el = document.querySelector('div.plyr__video-wrapper')
    if (!el) {
      return [0, 0]
    }
    const videoWidth = el.clientWidth
    const videoHeight = el.clientHeight
    const videoCenterX = Number.parseInt(el.clientLeft + videoWidth / 2)
    const videoCenterY = Number.parseInt(el.clientTop + videoHeight / 2)
    return [videoCenterX, videoCenterY]
  }

  function applySpinnerContainerCentering () {
    const [x, y] = getVideoCenterPoint()
    spinContainer.style.left = Number.parseInt(x - spinContainer.clientWidth / 2) + 'px'
    spinContainer.style.top = Number.parseInt(y - spinContainer.clientHeight / 2) + 'px'
  }

  function applyPlayBtnCentering () {
    const [x, y] = getVideoCenterPoint()
    playBtn.style.left = Number.parseInt(x - playBtn.clientWidth / 2) + 'px'
    playBtn.style.top = Number.parseInt(y - playBtn.clientHeight / 2) + 'px'
  }

  function onResize () {
    applySpinnerContainerCentering()
    applyPlayBtnCentering()
  }

  // on window size change
  onResize()
  // TODO: Use a mutation observer and only call onResize() when the video size changes.
  setInterval(onResize)
  // window.onresize = onResize

  // Autoplay the video
  spinContainer.classList.add('active')
  let jobId = null
  function oncanplay () {
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

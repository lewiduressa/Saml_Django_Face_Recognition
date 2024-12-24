var size = 400
var video = document.getElementById('stream-video-element')
video.setAttribute('playsinline', '')
video.setAttribute('autoplay', '')
video.setAttribute('muted', '')
video.style.width = `${size}px`

/* Setting up the constraint */
var facingMode = "user"; // Can be 'user' or 'environment' to access back or front camera (NEAT!)
var constraints = {
  audio: false,
  video: {
   facingMode: facingMode
  }
};

/* Stream it to video element */
navigator.mediaDevices.getUserMedia(constraints)
.then(function success(stream) {
    video.srcObject = stream;
    console.log('Successfully streaming...')
}).catch(function error(err) {
    console.log('Error accessing webcam...')
});

const BTN = document.getElementById('snapshot')
BTN.onclick = (e) => {
  e.preventDefault()
  snapshot()
  submitPhoto(e)
  BTN.setAttribute('disabled', 'true')
  BTN.innerText = 'Submitted'
}

document.getElementById('new_user').onclick = (e) => {
  document.getElementById('new_user').classList.add('d-none')
  document.getElementsByTagName('form')[0].classList.remove('d-none')
}

function submitPhoto(e) {
  let xhr = new XMLHttpRequest()
  let url = 'https://localhost:8000/face-rec/'

  xhr.onload = function() {
    if (xhr.status == 200) {
      console.log('Successfully received')
    } else {
      console.log('Error: Response not valid')
    }
  }

  xhr.open('POST', url, true)
  xhr.setRequestHeader('Content-Type', 'application/json')
  xhr.send(JSON.stringify({
    base64img: canvas.toDataURL()
  }))
}

setInterval(sendPic,3000)

function sendPic() {
  let canvas2 = document.getElementById("myCanvas2")
  canvas2.style.width = `${size/2}px`
  canvas2.style.border = '2px dashed black'
  canvas2.width = video.videoWidth
  canvas2.height = video.videoHeight
  let ctx2 = canvas2.getContext('2d');
  ctx2.scale(-1,1)
  ctx2.translate(-canvas2.width, 0);
  ctx2.drawImage(video, 0,0);

  let xhr = new XMLHttpRequest()
  let url = 'https://localhost:8000/face-rec2/'

  xhr.onload = function() {
    let data = JSON.parse(xhr.responseText)
    if (xhr.status == 200) {
      document.getElementById('name').innerText = ' '+data.name
      console.log(data.message)
    } else {
      console.log(data.message)
    }
  }

  xhr.open('POST', url, true)
  xhr.setRequestHeader('Content-Type', 'application/json')
  xhr.send(JSON.stringify({
    base64img: canvas2.toDataURL()
  }))
}

function snapshot() {
  // Draws current image from the video element into the canvas
  canvas = document.getElementById("myCanvas")
  canvas.classList.remove('d-none')
  canvas.style.width = `${size/2}px`
  canvas.style.border = '2px dashed black'
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  ctx = canvas.getContext('2d');
  ctx.scale(-1,1)
  ctx.translate(-canvas.width, 0);
  ctx.drawImage(video, 0,0);
}
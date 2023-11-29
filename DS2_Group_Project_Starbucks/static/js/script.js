document.addEventListener('DOMContentLoaded', function() {
    const micButton = document.getElementById('micButton');
    const transcriptDiv = document.getElementById('transcript');
    const voiceResponseDiv = document.getElementById('voiceResponse'); 
    const checkoutButton = document.getElementById('Checkout');
    
        // In your main page JavaScript
checkoutButton.addEventListener('click', function(event) {
    event.preventDefault();
    window.location.href = '/checkout'; // Redirect to the checkout route
});


        checkoutButton.addEventListener('click', function(event){
            event.preventDefault(); // Prevent the default button action
            fetch('/checkout')
                .then(response => {
                    // Process the response or redirect the user
                    event.preventDefault();
                    window.location.href = response.url; // Redirect to the response URL
                });
        });
    
     
   

    micButton.addEventListener('click', function() {
        fetch('/voice_order')
            .then(response => response.json())
            .then(data => {
                // Update the UI with the message from the server
                if (data.message) {
                    voiceResponseDiv.innerText = data.message; // Update the new div with the message
                }

                // Play audio from the URL
                if (data.audioUrl) {
                    const audio = new Audio(data.audioUrl);
                    audio.play();
                }

                // If the order is confirmed, update the Order Summary
                if (data.orderConfirmed) {
                    transcriptDiv.innerText = "Order Summary: \n" + data.confirmedOrder;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                voiceResponseDiv.innerText = "Error in processing the request."; // Display error message
            });
    });
    

        
    document.getElementById('micButton').addEventListener('click', function() {
        this.classList.toggle('recording');
    });
    });
    


 
    let mediaRecorder;
    let audioChunks = [];
    
    document.getElementById('micButton').addEventListener('mousedown', function() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                mediaRecorder.ondataavailable = event => {
                    audioChunks.push(event.data);
                };
                mediaRecorder.start();
            });
    });
    
    document.getElementById('micButton').addEventListener('mouseup', function() {
        if (mediaRecorder) {
            mediaRecorder.stop();
            mediaRecorder.onstop = () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                sendAudioToServer(audioBlob);
                audioChunks = [];
            };
        }
    });
    
    function sendAudioToServer(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'audio.wav');
    
        fetch('/upload_audio', {
            method: 'POST',
            body: formData
        }).then(response => response.text())
        .then(data => {
            console.log(data); // Log the response from Flask (recognized text)
        });
    }

    

const sendButton = document.getElementById("sendButton");
const messageInput = document.getElementById("messageInput");
const chatlog = document.getElementById("chatlog");
const usernameInput = document.getElementById("usernameInput");
const urlParams = new URLSearchParams(window.location.search);
const roomid = urlParams.get('roomid');

// send message
sendButton.addEventListener("click", () => {
    let username = usernameInput.value
    if (usernameInput.value === "") {
        username = "Anonymous"
    }
    console.log(messageInput.value)
    fetch('/upload_message', {
        method: 'POST',
        body: JSON.stringify({
            'username': username,
            'text': messageInput.value,
            'roomid': roomid
        })
    })
    messageInput.value = "";
})

function fetchNewMessages() {
    fetch('/get_messages', {    
        method: 'POST',
        headers: {
            roomid: roomid,
        }
    }).then(response => response.json())
    .then(data => {
        if (data.messages.length > 0) {
            updateChatWindow(data.messages);
        }
    })
    .catch(error => console.error('Error fetching messages:', error));
}

function updateChatWindow(messages) {
    chatlog.innerHTML = '';
    messages.forEach(message => {
        let messageElement = document.createElement('div');
        messageElement.textContent = `${message.username}: ${message.message}`;
        chatlog.appendChild(messageElement);
    });
}

fetchNewMessages();
setInterval(fetchNewMessages, 1000);
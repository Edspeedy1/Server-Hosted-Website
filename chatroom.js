const sendButton = document.getElementById("sendButton");
const messageInput = document.getElementById("messageInput");
const chatlog = document.getElementById("chatlog");
const usernameInput = document.getElementById("usernameInput");
const urlParams = new URLSearchParams(window.location.search);
const roomid = urlParams.get('roomid');
const roomiddisplay = document.getElementById("roomIdDisplay");
roomiddisplay.textContent = "Room ID: " + roomid;

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
messageInput.addEventListener("keyup", (event) => {
    if (event.key === "Enter") {
        event.preventDefault();
        sendButton.click();
    }
})

messageInput.addEventListener("input", function() {
    this.style.height = "auto";
    this.style.height = this.scrollHeight + "px";
});

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
    messages.forEach(message => {
        if (chatlog.children.length == 0 || message.timestamp > chatlog.children[chatlog.children.length - 1].timestamp) {
            let messageElement = document.createElement('div');
            messageElement.textContent = `${message.username}: ${message.message}`;
            messageElement.timestamp = message.timestamp;
            chatlog.appendChild(messageElement);
        }
    });
}

fetchNewMessages();
setInterval(fetchNewMessages, 1000);
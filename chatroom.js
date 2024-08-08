const sendButton = document.getElementById("sendButton");
const messageInput = document.getElementById("messageInput");
const chatlog = document.getElementById("chatlog");
const usernameInput = document.getElementById("usernameInput");
const urlParams = new URLSearchParams(window.location.search);
const roomid = urlParams.get('roomid');
const roomiddisplay = document.getElementById("roomIdDisplay");
roomiddisplay.textContent = "Room ID: " + roomid;

const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const socketUrl = `${protocol}//${window.location.hostname}:8765/${roomid}`;
const socket = new WebSocket(socketUrl);

socket.onmessage = function(event) {
    const newMessage = JSON.parse(event.data);
    updateChatWindow([newMessage]);
};

// send message
sendButton.addEventListener("click", () => {
    console.log(messageInput.value.replace(/\s+/g, '') == "");
    if (messageInput.value.replace(/\s+/g, '') == "") {
        messageInput.value = "";
        return;
    }
    let username = usernameInput.value
    if (usernameInput.value === "") {
        username = "Anonymous"
    }
    chatlog.scrollTop = chatlog.scrollHeight;
    fetch('/upload_message', {
        method: 'POST',
        body: JSON.stringify({
            'username': username,
            'text': messageInput.value,
            'roomid': roomid
        })
    })
    setTimeout(() => {
        chatlog.scrollTop = chatlog.scrollHeight;
        messageInput.value = "";
    }, 100);
})
messageInput.addEventListener("keydown", (event) => {
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
        chatlog.scrollTop = chatlog.scrollHeight;
    })
    .catch(error => console.error('Error fetching messages:', error));

}

function updateChatWindow(messages) {
    // if scrolled to bottom, scroll to bottom
    let flag = chatlog.scrollTop + chatlog.offsetHeight >= chatlog.scrollHeight;
        
    messages.forEach(message => {
        if (chatlog.children.length == 0 || message.timestamp > chatlog.children[chatlog.children.length - 1].timestamp) {
            let messageElement = document.createElement('div');
            messageElement.textContent = `${message.username}: ${message.message}`;
            messageElement.timestamp = message.timestamp;
            chatlog.appendChild(messageElement);
        }
    });

    if (flag) {
        chatlog.scrollTop = chatlog.scrollHeight;
    }
}

fetchNewMessages();
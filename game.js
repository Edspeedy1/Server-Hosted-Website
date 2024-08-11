const sendButton = document.getElementById("sendButton");
const messageInput = document.getElementById("messageInput");
const chatlog = document.getElementById("chatlog");
const urlParams = new URLSearchParams(window.location.search);

// send message
sendButton.addEventListener("click", () => {
    if (messageInput.value.replace(/\s+/g, '') == "") {
        messageInput.value = "";
        return;
    }

    chatlog.scrollTop = chatlog.scrollHeight;
    fetch('/upload_message', {
        method: 'POST',
        body: JSON.stringify({
            'session': getCookie("session"),
            'text': messageInput.value,
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log(data);
        if (data.error == "Invalid session") {
            alert("please Login first");
            window.location.href = `./index.html`;
        }
    })
    updateChatWindow([{
        'message': messageInput.value,
        'username': getCookie("username"),
        'timestamp': Date.now()
    }]);
    setTimeout(() => {
        chatlog.scrollTop = chatlog.scrollHeight;
        messageInput.value = "";
        messageInput.style.height = "19px";
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
    console.log(messages)
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

function getCookie(name) {
    const nameEQ = name + "=";
    const ca = document.cookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) === ' ') c = c.substring(1, c.length);
        if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
    }
    return null;
}

fetchNewMessages();
setInterval(fetchNewMessages, 2000);
const sendButton = document.getElementById("sendButton");
const messageInput = document.getElementById("messageInput");
const chatlog = document.getElementById("chatlog");
const urlParams = new URLSearchParams(window.location.search);
const colorTheme = urlParams.get('theme');


if (colorTheme) {
    if (colorTheme == "dark") {
        document.documentElement.style.setProperty('--textColor', '#ffffff'); // text
        document.documentElement.style.setProperty('--col1', '#111213'); // background
        document.documentElement.style.setProperty('--col2', '#000000'); // border
        document.documentElement.style.setProperty('--col3', '#595959'); // mid background
        document.documentElement.style.setProperty('--col4', '#979798'); // top background
    } else if (colorTheme == "inverse") {
        document.documentElement.style.setProperty('--textColor', '#ffffff');
        document.documentElement.style.setProperty('--col1', '#000000');
        document.documentElement.style.setProperty('--col2', '#ffffff');
        document.documentElement.style.setProperty('--col3', '#5f5f5f');
        document.documentElement.style.setProperty('--col4', '#a3a3a3');
    } else if (colorTheme == "ocean") {
        document.documentElement.style.setProperty('--textColor', '#ffffff');
        document.documentElement.style.setProperty('--col1', '#05033b');
        document.documentElement.style.setProperty('--col2', '#000208');
        document.documentElement.style.setProperty('--col3', '#4f6e8e');
        document.documentElement.style.setProperty('--col4', '#364650');
    } else if (colorTheme == "mcdonald") {
        document.documentElement.style.setProperty('--textColor', '#000000');
        document.documentElement.style.setProperty('--col1', '#ad0c00');
        document.documentElement.style.setProperty('--col2', '#ffd30f');
        document.documentElement.style.setProperty('--col3', '#ff6b61');
        document.documentElement.style.setProperty('--col4', '#f7ffad');
    } 
}

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
        'timestamp': parseInt(Date.now() / 1000 - 1),
        'temp': true
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
        chatlog.scrollTop = chatlog.scrollHeight;
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
    })
    .catch(error => console.error('Error fetching messages:', error));

}

function updateChatWindow(messages) {
    // if scrolled to bottom, scroll to bottom
    let flag = chatlog.scrollTop + chatlog.offsetHeight >= chatlog.scrollHeight;

    messages.forEach(message => {
        if (chatlog.children.length == 0) {
            let messageElement = document.createElement('div');
            if (message.temp) {
                messageElement.temp = true;
            }
            messageElement.textContent = `${message.username}: ${message.message}`;
            messageElement.timestamp = message.timestamp;
            chatlog.appendChild(messageElement);
        }
        else if (message.timestamp > chatlog.children[chatlog.children.length - 1].timestamp) {
            if (chatlog.children[chatlog.children.length - 1].temp) {
                chatlog.children[chatlog.children.length - 1].remove();
            }
            let messageElement = document.createElement('div');
            messageElement.textContent = `${message.username}: ${message.message}`;
            messageElement.timestamp = message.timestamp;
            if (message.temp) {
                messageElement.temp = true;
            }
            chatlog.appendChild(messageElement);
        }
    });

    if (flag) {
        chatlog.scrollTop = chatlog.scrollHeight;
        flag = false;
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
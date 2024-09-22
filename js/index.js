const joinButton = document.getElementById("joinButton");
const guestButton = document.getElementById("guestButton");
const usernameInput = document.getElementById("usernameInput");
const passwordShow = document.getElementById("passwordButton");
const passwordInput = document.getElementById("passwordInput");
const themeSelect = document.getElementById("themeSelect");

passwordShow.addEventListener("click", () => {
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        passwordShow.textContent = "Hide";
    } else {
        passwordInput.type = "password";
        passwordShow.textContent = "Show";
    }
})

// when enter is pressed, or button is clicked
joinButton.addEventListener("click", () => {
    if (usernameInput.value === "" || usernameInput.value.startsWith("Guest")) {
        alert("Please enter a username");
        return;
    }
    if (passwordInput.value === "") {
        alert("Please enter a password");
        return;
    }

    fetch('/login', {
        method: 'POST',
        body: JSON.stringify({
            'username': usernameInput.value,
            'password': passwordInput.value
        })
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(data.session);
            window.location.href = `./game?theme=${themeSelect.value}`;
        } else {
            alert("Incorrect username or password");
        }
    })
});

// when enter is pressed
passwordInput.addEventListener("keyup", (event) => {
    if (event.key === "Enter") {
        joinButton.click();
    }
})

guestButton.addEventListener("click", () => {
    fetch('/login', {
        method: 'POST',
        body: JSON.stringify({
            'username': "Guest" + "_" + makeid(3),
            'password': ""
        })
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            window.location.href = `./game?theme=${themeSelect.value}`;
        } else {
            alert("Incorrect username or password");
        }
    })
})


function makeid(length) {
    let result = '';
    const characters = 'abcdefghijklmnopqrstuvwxyz0123456789';
    const charactersLength = characters.length;
    let counter = 0;
    while (counter < length) {
      result += characters.charAt(Math.floor(Math.random() * charactersLength));
      counter += 1;
    }
    return result;
}

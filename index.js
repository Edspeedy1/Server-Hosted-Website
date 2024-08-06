const joinButton = document.getElementById("joinButton");
const createButton = document.getElementById("createButton");
const joinIdInput = document.getElementById("joinIdInput");

// when enter is pressed, or button is clicked
joinButton.addEventListener("click", () => {
    if (joinIdInput.value === "") {
        alert("Please enter a room ID");
        return;
    }
    window.location.href = `./chatRoom.html?roomid=${joinIdInput.value}`;
});

// when enter is pressed
joinIdInput.addEventListener("keyup", (event) => {
    if (event.key === "Enter") {
        joinButton.click();
    }
})

createButton.addEventListener("click", () => {
    window.location.href = `./chatRoom.html?create=${makeid(3) + "-" + makeid(3)}`;
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
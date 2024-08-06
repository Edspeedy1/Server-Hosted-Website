const joinButton = document.getElementById("joinButton");
const createButton = document.getElementById("createButton");
const joinIdInput = document.getElementById("joinIdInput");
const customIdInput = document.getElementById("customIdInput");

joinButton.addEventListener("click", () => {
    if (joinIdInput.value === "") {
        alert("Please enter a room ID");
        return;
    }
    window.location.href = `./chatRoom.html?join=${joinIdInput.value}`;
});

createButton.addEventListener("click", () => {
    if (customIdInput.value === "") {
        //  make a randon 6 character string
        customIdInput.value = makeid(3) + "-" + makeid(3);
    }
    // window.location.href = `./chatRoom.html?create=${customIdInput.value}`;
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
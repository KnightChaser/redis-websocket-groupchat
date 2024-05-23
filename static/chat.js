let ws;                         // This will hold the WebSocket connection
let isConnected = false;        // This will be used to check if the WebSocket connection is established

// Connect to the WebSocket server
function connect() {
    const username = document.getElementById("username").value;
    if (!username) {
        alert("Please enter a username.");
        return;
    }

    // Connect to the websocket server and maintain the connection until the user closes the browser
    ws = new WebSocket("ws://localhost:8000/ws");
    ws.onopen = function(event) {
        ws.send(JSON.stringify({ "username": username }));
        isConnected = true;
    };
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        if (data.content === "User list update") {
            // Update the list of currently connected users
            updateUserList(data.user_list);
        } else {
            // Append the message to the chat window
            const messages = document.getElementById('messages');
            const message = document.createElement('div');
            message.className = 'mb-2';
            message.innerHTML = `[${data.timestamp}] <strong>${data.username}</strong>: ${data.content}`;
            messages.appendChild(message);

            // Scroll to the bottom of the chat window to show the latest message
            messages.scrollTop = messages.scrollHeight;
        }
    };

    // Close the WebSocket connection when the user closes the browser
    ws.onclose = function(event) {
        isConnected = false;
    };
}

// Send a message to the WebSocket server
function sendMessage(event) {
    const input = document.getElementById("messageText");
    const username = document.getElementById("username").value;

    // If the WebSocket connection is not established yet, try to connect and send the message
    if (!isConnected) {
        connect();
        setTimeout(() => {
            if (isConnected) {
                ws.send(JSON.stringify({ "content": input.value }));
                input.value = '';
                input.focus();
            }
        }, 1000);
    } else {
        ws.send(JSON.stringify({ "content": input.value }));
        input.value = '';
        input.focus();
    }

    // Prevent the form from submitting
    if (event) {
        event.preventDefault();
    }
}

// Update the currently connected users list
function updateUserList(userList) {
    const userListElem = document.getElementById('user_list');
    userListElem.innerHTML = '';
    userList.forEach(function(user) {
        const userElem = document.createElement('li');
        userElem.className = 'p-2 bg-gray-200 rounded';
        userElem.textContent = user;
        userListElem.appendChild(userElem);
    });
}

// hit ctrl + enter to send the message
document.getElementById("messageText").addEventListener("keydown", function(event) {
    if (event.ctrlKey && event.key === "Enter") {
        sendMessage(event);
    }
});

// hit enter to connect
document.getElementById("username").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        connect();
    }
});

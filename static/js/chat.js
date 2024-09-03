document.addEventListener("DOMContentLoaded", function() {
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chatMessages');

    sendButton.addEventListener('click', function() {
        const userMessage = chatInput.value;
        if (userMessage.trim() === "") return;

        appendMessage(userMessage, 'user-message');

        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage })
        })
        .then(response => response.json())
        .then(data => {
            appendMessage(data.response, 'bot-message');
        })
        .catch(error => {
            console.error('Error:', error);
        });

        chatInput.value = "";
    });

    function appendMessage(message, className) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', className);
        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.innerHTML = `<p>${message}</p>`;
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});

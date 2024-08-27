document.addEventListener('DOMContentLoaded', function() {
    const chatButton = document.querySelector('.chatbot-button');
    const chatWindow = document.querySelector('.chat-window');
    const chatClose = document.querySelector('.chat-close');
    const chatInput = document.querySelector('.chat-input input');
    const chatSend = document.querySelector('.chat-input button');
    const chatMessages = document.querySelector('.chat-messages');

    chatButton.addEventListener('click', () => {
        chatWindow.style.display = 'flex';
    });

    chatClose.addEventListener('click', () => {
        chatWindow.style.display = 'none';
    });

    chatSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const message = chatInput.value.trim();
        if (message) {
            addMessage('user', message);
            chatInput.value = '';
            // Here you would typically send the message to a server
            // and get a response. For now, we'll just echo the message.
            setTimeout(() => {
                addMessage('bot', `You said: ${message}`);
            }, 1000);
        }
    }

    function addMessage(sender, text) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${sender}-message`);
        messageElement.textContent = text;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});
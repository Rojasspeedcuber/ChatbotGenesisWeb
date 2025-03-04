// Bible Chatbot - Chat Interface JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.getElementById('messageForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');
    
    // Initialize chat
    initChat();
    
    function initChat() {
        // Focus on input field
        messageInput.focus();
        
        // Scroll to bottom of chat
        scrollToBottom();
        
        // Load chat history if exists in session storage
        loadChatHistory();
    }
    
    // Load chat history from session storage
    function loadChatHistory() {
        const history = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');
        
        if (history.length > 0) {
            // Clear welcome message if history exists
            chatMessages.innerHTML = '';
            
            // Add messages from history
            history.forEach(msg => {
                addMessage(msg.message, msg.sender);
            });
            
            scrollToBottom();
        }
    }
    
    // Save chat history to session storage
    function saveChatHistory(message, sender) {
        const history = JSON.parse(sessionStorage.getItem('chatHistory') || '[]');
        history.push({
            message: message,
            sender: sender,
            timestamp: new Date().toISOString()
        });
        sessionStorage.setItem('chatHistory', JSON.stringify(history));
    }
    
    // Clear chat history
    function clearChatHistory() {
        sessionStorage.removeItem('chatHistory');
        chatMessages.innerHTML = '';
        
        // Add welcome message
        addMessage(`Olá! Sou o Chatbot Gênesis WEB, um assistente especializado na Bíblia Sagrada. Como posso ajudar você hoje?`, 'bot');
    }
    
    // Show loading indicator
    function showLoading() {
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message bot-message loading';
        loadingDiv.id = 'loadingMessage';
        loadingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(loadingDiv);
        scrollToBottom();
    }
    
    // Hide loading indicator
    function hideLoading() {
        const loadingMessage = document.getElementById('loadingMessage');
        if (loadingMessage) {
            loadingMessage.remove();
        }
    }
    
    // Add message to chat
    function addMessage(message, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Format message content
        const formattedMessage = formatMessage(message);
        
        messageContent.innerHTML = formattedMessage;
        messageDiv.appendChild(messageContent);
        
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
        
        // Save message to history
        saveChatHistory(message, sender);
    }
    
    // Format message with markdown and Bible references
    function formatMessage(message) {
        // Convert line breaks to <br>
        let formatted = message.replace(/\n/g, '<br>');
        
        // Highlight Bible references (e.g., João 3:16, Gênesis 1:1-3)
        formatted = formatted.replace(/([1-3]?\s*[A-Za-zÀ-ÖØ-öø-ÿ]+\s+\d+:\d+(?:-\d+)?)/g, 
            '<span class="bible-reference">$1</span>');
        
        // Add simple markdown for bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Add simple markdown for italic text
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return formatted;
    }
    
    // Scroll to bottom of chat
    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Send message to API
    async function sendMessage(message) {
        try {
            showLoading();
            
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            hideLoading();
            addMessage(data.message, 'bot');
        } catch (error) {
            console.error('Error sending message:', error);
            hideLoading();
            addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.', 'bot');
        }
    }
    
    // Handle form submission
    messageForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (message) {
            // Clear input
            messageInput.value = '';
            
            // Add user message to chat
            addMessage(message, 'user');
            
            // Send to API
            sendMessage(message);
            
            // Focus back on input
            messageInput.focus();
        }
    });
    
    // Add clear chat button functionality if it exists
    const clearButton = document.getElementById('clearChat');
    if (clearButton) {
        clearButton.addEventListener('click', function() {
            clearChatHistory();
        });
    }
    
    // Handle Ctrl+Enter to submit
    messageInput.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            messageForm.dispatchEvent(new Event('submit'));
        }
    });
});
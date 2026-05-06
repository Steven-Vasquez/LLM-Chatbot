import { connectDebugSocket } from './debugSocket.js';
require('dotenv').config();

// ===============================
// Chat App Main Logic
// ===============================

let currentChatId = null;
const username = 'Human'; // Temporary until session/user system is implemented

// --- Test SQL Connection on load ---
async function testSQLConnection() {
    try {
        const res = await fetch('http://localhost:5000/api/chat/test-sql', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
        });
        if (!res.ok) throw new Error(`AI request failed: ${res.status}`);
        const data = await res.json();
        console.log("SQL Test Response:", data);
    } catch (err) {
        console.error("Error testing SQL connection:", err);
    }
}
testSQLConnection();

// --- Load/refresh all chats into sidebar ---
async function loadChats() {
    let text = "";
    try {
        const res = await fetch(`http://localhost:5000/api/chat/get-active-chats`);
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        text = await res.text();
        //console.log("Active chats response:", text);
    } catch (error) {
        console.error("Error fetching active chats:", error);
    }
    try {
        const chats = JSON.parse(text);
        const list = document.getElementById('chat-list');
        list.innerHTML = '';
        chats.forEach(chat => {
            const div = document.createElement('div');
            div.textContent = chat.user + ' (' + new Date(chat.last_updated).toLocaleTimeString() + ')';
            div.className = 'chat-item' + ((currentChatId !== null && parseInt(chat.chat_id) === parseInt(currentChatId)) ? ' active' : '');
            div.onclick = () => selectChat(chat.chat_id);
            list.appendChild(div);
        });
    } catch (e) {
        console.error('JSON parse error:', e);
    }
}

// --- Create a new chat and set as current ---
async function createChat() {
    let data = "";
    try {
        const res = await fetch('http://localhost:5000/api/chat/create-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: username })
        });
        data = await res.json();
        if (!res.ok) {
            console.error("Server Error:", data.error);
        } else {
            console.log("New chat created with ID: ", data.chat_id);
        }
    } catch (err) {
        console.error("Fetch failed:", err);
    }
    currentChatId = data.chat_id;
    await loadChats();
    await fetchMessages();
}

// --- Select a chat and load chat session by ID ---
async function selectChat(chatId) {
    currentChatId = chatId;
    await fetchMessages();
    loadChats();
    connectDebugSocket(currentChatId);
}

// --- Fetch messages for current chat ---
async function fetchMessages() {
    const box = document.getElementById('chat-box');
    if (!currentChatId) {
        box.innerHTML = '';
        return;
    }
    try {
        const res = await fetch(`http://localhost:5000/api/chat/get-chat-messages?chat_id=${encodeURIComponent(currentChatId)}`);
        if (!res.ok) throw new Error(`HTTP error! Status: ${res.status}`);
        const messages = await res.json();
        box.innerHTML = messages.map(msg => `
            <div class='message'>
                <span><strong>${escapeHtml(msg.user)}</strong>: ${escapeHtml(msg.message)}</span>
            </div>
        `).join("");
    } catch (error) {
        console.error('Error fetching messages:', error);
        box.innerHTML = `<p style="color: red;">Failed to load messages. Please try again later.</p>`;
    }
}

// --- Helper function to escape HTML (prevent XSS) ---
function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// --- Periodically refresh messages ---
setInterval(fetchMessages, 2000);
loadChats();

// --- Listener: Create a new chat ---
document.getElementById('new-chat-btn').addEventListener('click', async () => {
    currentChatId = null;
    fetchMessages();
    loadChats();
});

// ===============================
// Customization controls (mode + tools)
// ===============================

// --- Clear Debug Output Button ---
document.addEventListener('DOMContentLoaded', () => {
    const clearDebugBtn = document.getElementById('clear-debug-btn');
    const debugContent = document.getElementById('debug-content');
    if (clearDebugBtn && debugContent) {
        clearDebugBtn.addEventListener('click', () => {
            debugContent.innerHTML = '';
        });
    }
});

function getSelectedMode() {
    const active = document.querySelector(".mode-option.active");
    return active ? active.dataset.mode : "basic";
}

function getEnabledTools() {
    return Array.from(document.querySelectorAll(".tool-chip.active"))
        .map(chip => chip.dataset.tool);
}

function updateToolRowState() {
    const toolRow = document.querySelector(".tool-row");
    const mode = getSelectedMode();
    if (toolRow) {
        if (mode === "basic") {
            toolRow.style.opacity = "0.4";
            toolRow.style.pointerEvents = "none";
            // Clear tool selections visually
            document.querySelectorAll(".tool-chip")
                .forEach(t => t.classList.remove("active"));
        } else {
            toolRow.style.opacity = "1";
            toolRow.style.pointerEvents = "auto";
        }
    }
}

// --- Mode selection ---
document.querySelectorAll(".mode-option").forEach(option => {
    option.addEventListener("click", () => {
        document.querySelectorAll(".mode-option")
            .forEach(o => o.classList.remove("active"));
        option.classList.add("active");
        updateToolRowState();
    });
});

// --- Tool chip toggles (purely visual) ---
document.querySelectorAll(".tool-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        // Only allow toggling if not in basic mode
        if (getSelectedMode() === "basic") return;
        chip.classList.toggle("active");
    });
});

// --- Initialize tool row state on page load ---
document.addEventListener("DOMContentLoaded", updateToolRowState);

// ===============================
// Message Submission Handler
// ===============================

document.getElementById('chat-form').addEventListener('submit', async e => {
    e.preventDefault();
    const messageInput = document.getElementById('message');
    const userMessage = messageInput.value.trim();
    if (!userMessage) return;

    try {
        // Step 1: Ensure a chat is selected
        if (!currentChatId) {
            // Create and select new chat if none is selected
            await createChat();
            selectChat(currentChatId);
        }

        // Step 2: Add Human message to DB
        const postRes = await fetch('http://localhost:5000/api/chat/post-message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: username, message: userMessage, chat_id: currentChatId })
        });
        if (!postRes.ok) throw new Error(`Failed to post user message: ${postRes.status}`);

        // Clear input and refresh messages+chats
        messageInput.value = '';
        fetchMessages();
        loadChats();

        const currentMode = getSelectedMode();
        if (currentMode === "basic") {
            // Step 3: Get chat history (formatted)
            const historyRes = await fetch(`http://localhost:5000/api/chat/get-chat-history/${encodeURIComponent(currentChatId)}`);
            if (!historyRes.ok) throw new Error(`Failed to fetch chat history: ${historyRes.status}`);
            const chatHistory = await historyRes.text();
            // Step 4: Build prompt and send to Ollama
            const buildPromptRes = await fetch(
                `http://localhost:5000/api/build-prompt/${currentChatId}`,
                { method: 'GET' }
            );
            if (!buildPromptRes.ok) throw new Error(`Failed to build prompt: ${buildPromptRes.status}`);
            const { prompt } = await buildPromptRes.json();
            // Step 5: Get AI response
            const aiResponse = await fetch('http://localhost:5000/api/send-ollama-prompt', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: prompt })
            });
            if (!aiResponse.ok) throw new Error(`AI request failed: ${aiResponse.status}`);
            const data = await aiResponse.json();
            const aiReply = data.reply || "(No response)";
            // Step 6: Add Ollama's response to DB
            const aiPostRes = await fetch('http://localhost:5000/api/chat/post-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user: process.env.chatbot_name || "Ollama", message: aiReply, chat_id: currentChatId })
            });
            if (!aiPostRes.ok) throw new Error(`Failed to post user message: ${aiPostRes.status}`);
        } else if (currentMode === "agent") {
            // Step 3: Request Ollama agent response
            const currentTools = getEnabledTools();
            console.log("Requesting Ollama agent response for chat ID:", currentChatId);
            console.log("Mode:", currentMode);
            console.log("Tools:", currentTools);
            const agentResponse = await fetch(`http://localhost:5000/api/run-agent/${currentChatId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mode: currentMode, tools: currentTools })
            });
            if (!agentResponse.ok) throw new Error(`AI request failed: ${agentResponse.status}`);
            const aiData = await agentResponse.json();
            const aiReply = aiData.final_answer || "(No response)";
            // Step 4: Add Ollama's response to DB
            const aiPostRes = await fetch('http://localhost:5000/api/chat/post-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user: process.env.chatbot_name || "Ollama", message: aiReply, chat_id: currentChatId })
            });
            if (!aiPostRes.ok) throw new Error(`Failed to post user message: ${aiPostRes.status}`);
        }
        // Step 7: Refresh chat
        await fetchMessages();
    } catch (error) {
        console.error("Error in chat submission:", error);
    }
});

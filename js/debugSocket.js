// debugSocket.js

let debugSocket = null;

/**
 * Public function to connect debug WebSocket
 */
export function connectDebugSocket(chatId) {
    const debugDiv = document.getElementById("debug-content");

    if (!debugDiv) {
        console.warn("Debug container not found.");
        return;
    }

    // Close previous socket if switching chats
    if (debugSocket) {
        debugSocket.close();
    }

    debugSocket = new WebSocket(`ws://localhost:5000/ws/debug/${chatId}`);

    debugSocket.onopen = () => {
        console.log("Debug socket connected.");
        renderSystemMessage(debugDiv, "Connected to debug stream.");
    };

    debugSocket.onclose = () => {
        console.log("Debug socket closed.");
        renderSystemMessage(debugDiv, "Debug connection closed.");
    };

    debugSocket.onerror = (err) => {
        console.error("Debug socket error:", err);
        renderError(debugDiv, { message: "WebSocket error occurred." });
    };

    debugSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Debug event received:", data);

        routeEvent(debugDiv, data);
        debugDiv.scrollTop = debugDiv.scrollHeight;
    };
}

/**
 * Route events based on type
 */
function routeEvent(container, data) {
        
    switch (data.type) {
        case "websocket_connection":
            renderWebsocketConnection(container, data);
            break;
        case "iteration_start":
            renderIteration(container, data);
            break;

        case "system_prompt":
            renderSystemPrompt(container, data);
            break;

        case "llm_request":
            renderLLMRequest(container, data);
            break;

        case "llm_thinking":
            renderLLMThinking(container, data);
            break;
            
        case "tool_call":
            renderToolCall(container, data);
            break;

        case "tool_processing":
            renderToolProcessing(container, data);
            break;

        case "tool_result":
            renderToolResult(container, data);
            break;

        case "final_answer":
            renderFinalAnswer(container, data);
            break;

        case "error":
            renderError(container, data);
            break;

        default:
            console.warn("Unknown debug event type:", data.type);
    }
}

/* ---------------------------
   Render Functions
--------------------------- */
function renderWebsocketConnection(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-websocket");
    line.textContent = `WebSocket Connection: ${data.content || "Established"}`;
    container.appendChild(line);
}

function renderIteration(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-iteration");
    line.textContent = `===== Iteration ${data.iteration} =====`;
    container.appendChild(line);
}

function renderSystemPrompt(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-system");

    line.innerHTML = `<strong>System Prompt</strong>`;
    line.appendChild(createCollapsibleJSON(data.content));

    container.appendChild(line);
}

function renderLLMRequest(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-llm");

    line.innerHTML = `<strong>LLM Request Messages</strong>`;
    line.appendChild(createCollapsibleJSON(data.messages));

    container.appendChild(line);
}

function renderLLMThinking(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-llm-thinking");

    line.innerHTML = `<strong>🧠 LLM Thinking</strong>`;
    line.appendChild(createCollapsibleJSON(data.content));

    container.appendChild(line);
}

function renderToolCall(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-tool-call");

    line.innerHTML = `🔧 <strong>${data.tool}</strong>`;
    line.appendChild(createCollapsibleJSON(data.args));

    container.appendChild(line);
}

function renderToolProcessing(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-tool-processing");

    line.innerHTML = `⏳ <strong>Tool Processing Log</strong>`;
    line.appendChild(createCollapsibleJSON(data.log));
    container.appendChild(line);
}

function renderToolResult(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-tool-result");

    line.innerHTML = `📦 <strong>${data.tool} Result</strong>`;
    line.appendChild(createCollapsibleJSON(data.result));

    container.appendChild(line);
}

function renderFinalAnswer(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-final");

    line.innerHTML = `✅ <strong>Final Answer</strong>: ${data.content}`;
    container.appendChild(line);
}

function renderError(container, data) {
    const line = document.createElement("div");
    line.classList.add("debug-error");

    line.innerHTML = `❌ <strong>Error:</strong> ${data.message}`;
    container.appendChild(line);
}

function renderSystemMessage(container, message) {
    const line = document.createElement("div");
    line.classList.add("debug-system-msg");
    line.textContent = message;
    container.appendChild(line);
}

/* ---------------------------
   Utility
--------------------------- */

function createCollapsibleJSON(obj) {
    console.log(typeof obj, obj)
    const wrapper = document.createElement("div");

    const toggle = document.createElement("button");
    toggle.textContent = "Show / Hide";
    toggle.classList.add("debug-toggle");

    const pre = document.createElement("pre");
    pre.classList.add("collapsible-json");
    //pre.textContent = JSON.stringify(obj, null, 2);
    pre.textContent = JSON.stringify(obj, null, 2).replace(/\\n/g, "\n").replace(/\\"/g, '"').replace(/\\\\/g, "\\");
    pre.style.display = "none";

    toggle.onclick = () => {
        pre.style.display = pre.style.display === "none" ? "block" : "none";
    };

    wrapper.appendChild(toggle);
    wrapper.appendChild(pre);

    return wrapper;
}

// AI Q&A Chat client operations

let currentSessionId = null;

// Hook triggered by app.js when active document selection changes
function onActiveDocumentChange(docId) {
  const chatWorkspace = document.getElementById("chat-workspace-area");
  const noDocWarning = document.getElementById("no-doc-warning");
  const docTitle = document.getElementById("active-doc-title");
  const docSubtitle = document.getElementById("active-doc-subtitle");

  if (!docId) {
    if (chatWorkspace) chatWorkspace.style.display = "none";
    if (noDocWarning) noDocWarning.style.display = "flex";
    if (docTitle) docTitle.innerText = "AI Study Chat";
    if (docSubtitle) docSubtitle.innerText = "Please select a PDF file from the sidebar selector to start asking questions.";
    currentSessionId = null;
    return;
  }

  // Get filename from global lists
  const activeDoc = globalDocuments.find(d => Number(d.id) === Number(docId));
  const filename = activeDoc ? activeDoc.filename : "Selected Document";

  if (docTitle) docTitle.innerText = `Chat: ${filename}`;
  if (docSubtitle) docSubtitle.innerText = `AI answers questions based ONLY on ${filename}.`;
  
  if (chatWorkspace) chatWorkspace.style.display = "flex";
  if (noDocWarning) noDocWarning.style.display = "none";

  // Reset state
  currentSessionId = null;
  clearChatBox();
  
  // Display Welcome Message
  appendMessageToUI("ai", `Hello! I have fully indexed **${filename}**. Ask me any question about its contents. I will answer using verified source chunks and page citations.`, [], 100);

  // Load chat session listings
  loadChatSessionOptions(docId);
}

function clearChatBox() {
  const chatBox = document.getElementById("chat-messages-box");
  if (chatBox) chatBox.innerHTML = "";
}

/**
 * Loads list of past chat sessions for selected document
 */
async function loadChatSessionOptions(docId) {
  const select = document.getElementById("chat-session-select");
  if (!select) return;

  try {
    const response = await fetch(`/api/chat/sessions?document_id=${docId}`, {
      headers: getAuthHeaders()
    });

    if (!response.ok) throw new Error("Failed to load chat history.");

    const sessions = await response.json();
    
    if (sessions.length > 0) {
      select.style.display = "block";
      select.innerHTML = '<option value="">-- Recent Chats --</option>';
      sessions.forEach(s => {
        const option = document.createElement("option");
        option.value = s.id;
        option.textContent = s.title;
        if (Number(s.id) === Number(currentSessionId)) {
          option.selected = true;
        }
        select.appendChild(option);
      });
    } else {
      select.style.display = "none";
    }
  } catch (err) {
    console.error("Error loading chat sessions:", err);
  }
}

/**
 * Loads messages for a selected session ID
 */
async function loadSessionHistory(sessionId) {
  if (!sessionId) {
    // Clear and show welcome message again
    const activeDocId = localStorage.getItem("active_document_id");
    onActiveDocumentChange(activeDocId);
    return;
  }

  currentSessionId = sessionId;
  clearChatBox();

  try {
    const response = await fetch(`/api/chat/history/${sessionId}`, {
      headers: getAuthHeaders()
    });

    if (!response.ok) throw new Error("Failed to load message history.");

    const messages = await response.json();
    messages.forEach(msg => {
      appendMessageToUI(msg.sender, msg.message, msg.sources, msg.confidence);
    });
    scrollToBottom();
  } catch (err) {
    showToast(err.message, "danger");
  }
}

/**
 * Renders a chat bubble in the messages box
 */
function appendMessageToUI(sender, text, sources = [], confidence = null) {
  const chatBox = document.getElementById("chat-messages-box");
  if (!chatBox) return;

  const row = document.createElement("div");
  row.className = `chat-msg-row ${sender} animate-slideup`;

  // Format citations formatting e.g. [Page 4] as styled badges
  let formattedText = text;
  // Replace [Page X] with click-triggered badges
  formattedText = formattedText.replace(/\[Page\s+(\d+)\]/gi, (match, pageNum) => {
    return `<span class="citation-badge" onclick="highlightCitation(${pageNum})">Page ${pageNum}</span>`;
  });
  
  // Basic markdown bold mapping
  formattedText = formattedText.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

  let bubbleHTML = `<div class="chat-bubble">`;
  bubbleHTML += `<div style="white-space: pre-wrap;">${formattedText}</div>`;

  // Render confidence and citations for AI messages
  if (sender === "ai" && (confidence !== null || sources.length > 0)) {
    bubbleHTML += `<div class="chat-meta-row">`;
    
    if (confidence !== null) {
      bubbleHTML += `<span class="chat-meta-confidence">AI confidence: ${confidence.toFixed(1)}%</span>`;
    }
    
    if (sources.length > 0) {
      const sourceId = "source_" + Math.floor(Math.random() * 100000);
      bubbleHTML += `
        <span class="sources-toggle" onclick="toggleSourcesUI('${sourceId}')">
          <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2" fill="none"><path d="M12 5v14M5 12h14"/></svg>
          Show Source References (${sources.length})
        </span>
      `;
      
      bubbleHTML += `</div>`; // Close chat-meta-row
      
      // Inject collapsed source texts
      bubbleHTML += `<div class="sources-content" id="${sourceId}">`;
      sources.forEach(src => {
        bubbleHTML += `
          <div class="source-item">
            <div class="source-item-page">Page ${src.page}</div>
            <div>"${src.text}"</div>
          </div>
        `;
      });
      bubbleHTML += `</div>`;
    } else {
      bubbleHTML += `</div>`; // Close chat-meta-row
    }
  } else {
    bubbleHTML += `</div>`; // Close chat-bubble
  }

  row.innerHTML = bubbleHTML;
  chatBox.appendChild(row);
  scrollToBottom();
}

function toggleSourcesUI(id) {
  const el = document.getElementById(id);
  if (el) {
    const isVisible = el.style.display === "flex";
    el.style.display = isVisible ? "none" : "flex";
  }
}

function highlightCitation(page) {
  showToast(`Source referenced on Page ${page}`, "info");
}

function scrollToBottom() {
  const chatBox = document.getElementById("chat-messages-box");
  if (chatBox) {
    chatBox.scrollTop = chatBox.scrollHeight;
  }
}

// Form Submission Event
document.getElementById("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  
  const activeDocId = localStorage.getItem("active_document_id");
  if (!activeDocId) {
    showToast("Please select a document first.", "warning");
    return;
  }

  const textarea = document.getElementById("chat-input-text");
  const question = textarea.value.trim();
  if (!question) return;

  // Clear input
  textarea.value = "";
  
  // Disable submission
  const sendBtn = document.getElementById("chat-send-btn");
  sendBtn.disabled = true;
  textarea.disabled = true;

  // Append user bubble
  appendMessageToUI("user", question);

  // Append skeleton AI loader
  const loaderRow = document.createElement("div");
  loaderRow.className = "chat-msg-row ai animate-fadein";
  loaderRow.id = "chat-ai-loader";
  loaderRow.innerHTML = `
    <div class="chat-bubble">
      <div class="skeleton skeleton-text" style="width: 250px;"></div>
      <div class="skeleton skeleton-text" style="width: 180px;"></div>
    </div>
  `;
  document.getElementById("chat-messages-box").appendChild(loaderRow);
  scrollToBottom();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        document_id: Number(activeDocId),
        session_id: currentSessionId,
        question: question
      })
    });

    // Remove loader
    const loader = document.getElementById("chat-ai-loader");
    if (loader) loader.remove();

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Query failed.");
    }

    const data = await response.json();
    
    // Store session state
    const isNewSession = currentSessionId === null;
    currentSessionId = data.session_id;

    // Render response
    appendMessageToUI("ai", data.response.message, data.response.sources, data.response.confidence);

    if (isNewSession) {
      // Reload sessions dropdown list
      await loadChatSessionOptions(activeDocId);
      const select = document.getElementById("chat-session-select");
      if (select) select.value = currentSessionId;
    }

  } catch (err) {
    const loader = document.getElementById("chat-ai-loader");
    if (loader) loader.remove();
    appendMessageToUI("ai", `Error: ${err.message}. Please verify your network connection and API key settings.`);
  } finally {
    sendBtn.disabled = false;
    textarea.disabled = false;
    textarea.focus();
  }
});

// Trigger submit on Enter (without shift)
document.getElementById("chat-input-text").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    document.getElementById("chat-form").requestSubmit();
  }
});

// Auto-run trigger on selection checks
window.addEventListener("load", () => {
  const activeDocId = localStorage.getItem("active_document_id");
  onActiveDocumentChange(activeDocId);
});

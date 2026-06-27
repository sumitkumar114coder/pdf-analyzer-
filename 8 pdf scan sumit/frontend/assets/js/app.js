// Shared app layout controller and global utilities
requireAuth(); // Ensure page is protected

// Global State
let globalDocuments = [];
let activeDocumentId = localStorage.getItem("active_document_id") || null;

document.addEventListener("DOMContentLoaded", () => {
  // 1. Theme initialization
  initTheme();

  // 2. Inject standard sidebar
  injectSidebar();

  // 3. Page specific initialization
  initPage();
});

/**
 * Resolves current theme selection.
 */
function initTheme() {
  const currentTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", currentTheme);
  
  // Update theme switcher buttons on settings page if active
  const lightBtn = document.getElementById("theme-light-btn");
  const darkBtn = document.getElementById("theme-dark-btn");
  if (lightBtn && darkBtn) {
    if (currentTheme === "dark") {
      darkBtn.classList.add("active");
      lightBtn.classList.remove("active");
    } else {
      lightBtn.classList.add("active");
      darkBtn.classList.remove("active");
    }
  }
}

/**
 * Changes active color theme.
 */
function setTheme(theme) {
  localStorage.setItem("theme", theme);
  document.documentElement.setAttribute("data-theme", theme);
  showToast(`Switched to ${theme} mode`, "success");
  
  const lightBtn = document.getElementById("theme-light-btn");
  const darkBtn = document.getElementById("theme-dark-btn");
  if (lightBtn && darkBtn) {
    if (theme === "dark") {
      darkBtn.classList.add("active");
      lightBtn.classList.remove("active");
    } else {
      lightBtn.classList.add("active");
      darkBtn.classList.remove("active");
    }
  }
}

/**
 * Generates and injects the common sidebar HTML into #sidebar-container.
 */
function injectSidebar() {
  const container = document.getElementById("sidebar-container");
  if (!container) return;

  const currentPath = window.location.pathname;
  const isPageActive = (path) => currentPath.includes(path) ? "active" : "";

  const user = JSON.parse(localStorage.getItem(USER_INFO_KEY) || '{"username":"User"}');
  const avatarLetter = user.username.charAt(0).toUpperCase();

  const sidebarHTML = `
    <div class="sidebar animate-fadein">
      <div class="sidebar-header">
        <svg viewBox="0 0 24 24" stroke-width="2.5" fill="none">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>
        <span>Research Assistant</span>
      </div>

      <!-- Active Document Selector Dropdown -->
      <div class="sidebar-doc-selector">
        <label class="sidebar-doc-label">Active Document</label>
        <select class="doc-dropdown" id="sidebar-doc-dropdown" onchange="handleSidebarDocChange(this.value)">
          <option value="">-- Select PDF file --</option>
        </select>
      </div>

      <ul class="sidebar-menu">
        <li class="menu-item ${isPageActive('dashboard')}">
          <a href="/dashboard.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/>
              <rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/>
            </svg>
            <span>Dashboard</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('upload')}">
          <a href="/upload.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Upload PDF</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('chat')}">
          <a href="/chat.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <span>AI Chat Q&amp;A</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('summary')}">
          <a href="/summary.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
            </svg>
            <span>Auto Summary</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('flashcards')}">
          <a href="/flashcards.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
            </svg>
            <span>Flashcards</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('mcq')}">
          <a href="/mcq.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
              <line x1="9" y1="9" x2="15" y2="9"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="11" y2="17"/>
            </svg>
            <span>MCQ Generator</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('history')}">
          <a href="/history.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
            <span>Activity History</span>
          </a>
        </li>
        <li class="menu-item ${isPageActive('settings')}">
          <a href="/settings.html">
            <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
            <span>Settings</span>
          </a>
        </li>
      </ul>

      <div class="sidebar-footer">
        <div class="user-profile">
          <div class="user-avatar">${avatarLetter}</div>
          <div class="user-details">
            <span class="user-name">${user.username}</span>
          </div>
        </div>
        <button class="user-logout-btn" onclick="logout()" title="Logout">
          <svg viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
        </button>
      </div>
    </div>
  `;

  container.innerHTML = sidebarHTML;
  fetchAndPopulateSidebarDocs();
}

/**
 * Fetches the document list from API to populate sidebar selector
 */
async function fetchAndPopulateSidebarDocs() {
  try {
    const response = await fetch('/api/documents', {
      headers: getAuthHeaders()
    });

    if (response.status === 401) {
      logout();
      return;
    }

    if (!response.ok) throw new Error("Failed to fetch documents.");

    globalDocuments = await response.json();
    populateSidebarDocDropdown(globalDocuments);
  } catch (err) {
    console.error("Error loading sidebar documents:", err);
  }
}

/**
 * Renders the options list in the sidebar selector dropdown
 */
function populateSidebarDocDropdown(docs) {
  const dropdown = document.getElementById("sidebar-doc-dropdown");
  if (!dropdown) return;

  // Clear existing items but retain placeholder
  dropdown.innerHTML = '<option value="">-- Select PDF file --</option>';

  docs.forEach(doc => {
    const option = document.createElement("option");
    option.value = doc.id;
    option.textContent = doc.filename;
    if (Number(doc.id) === Number(activeDocumentId)) {
      option.selected = true;
    }
    dropdown.appendChild(option);
  });
}

/**
 * Handles dropdown changes to update local storage and notify active page
 */
function handleSidebarDocChange(val) {
  activeDocumentId = val || null;
  if (activeDocumentId) {
    localStorage.setItem("active_document_id", activeDocumentId);
    showToast("Active document updated", "success");
  } else {
    localStorage.removeItem("active_document_id");
  }

  // Trigger page-specific update if defined
  if (typeof onActiveDocumentChange === "function") {
    onActiveDocumentChange(activeDocumentId);
  }
}

// --- Page Specific Logic Route dispatcher ---
function initPage() {
  const path = window.location.pathname;

  if (path.includes("dashboard.html")) {
    loadDashboardData();
  } else if (path.includes("settings.html")) {
    loadSettingsData();
  }
}

// --- Dashboard Specific Functions ---
async function loadDashboardData() {
  try {
    // 1. Fetch Documents list
    const response = await fetch('/api/documents', {
      headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error("Failed to load documents.");
    const docs = await response.json();

    // 2. Fetch history statistics
    const histResponse = await fetch('/api/history', {
      headers: getAuthHeaders()
    });
    const historyLogs = histResponse.ok ? await histResponse.json() : [];

    // Calculate statistics
    document.getElementById("stat-uploads").innerText = docs.length;
    document.getElementById("stat-chats").innerText = historyLogs.filter(l => l.action_type === "chat").length;
    document.getElementById("stat-summaries").innerText = historyLogs.filter(l => l.action_type === "summary").length;
    document.getElementById("stat-mcqs").innerText = historyLogs.filter(l => l.action_type === "mcq").length;

    // Populate uploads table
    populateDashboardTable(docs);
  } catch (err) {
    showToast(err.message, "danger");
  }
}

function populateDashboardTable(docs) {
  const tableBody = document.getElementById("dashboard-table-body");
  if (!tableBody) return;

  if (docs.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="4" style="text-align: center; color: var(--text-tertiary); padding: 3rem 1rem;">
          No documents uploaded yet. Go to <a href="/upload.html" style="color: var(--primary); font-weight:600;">Upload</a> to get started.
        </td>
      </tr>
    `;
    return;
  }

  tableBody.innerHTML = "";
  docs.slice(0, 5).forEach(doc => {
    const dateStr = new Date(doc.upload_date).toLocaleDateString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric'
    });
    const sizeMB = (doc.file_size / (1024 * 1024)).toFixed(2) + " MB";

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <div class="doc-name-cell">
          <svg viewBox="0 0 24 24" stroke-width="2" fill="none">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
          </svg>
          <span>${doc.filename}</span>
        </div>
      </td>
      <td>${doc.page_count} pages</td>
      <td>${sizeMB}</td>
      <td>
        <div class="table-actions">
          <button class="action-btn" onclick="studyDocument(${doc.id})" title="Study document">
            <svg viewBox="0 0 24 24" stroke-width="2" fill="none" style="stroke: var(--primary);">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
            </svg>
          </button>
          <button class="action-btn" onclick="renameDocument(${doc.id}, '${doc.filename}')" title="Rename file">
            <svg viewBox="0 0 24 24" stroke-width="2" fill="none">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4z"/>
            </svg>
          </button>
          <button class="action-btn action-btn-delete" onclick="deleteDocument(${doc.id})" title="Delete file">
            <svg viewBox="0 0 24 24" stroke-width="2" fill="none">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </td>
    `;
    tableBody.appendChild(tr);
  });
}

function studyDocument(id) {
  localStorage.setItem("active_document_id", id);
  window.location.href = "/chat.html";
}

async function renameDocument(id, currentName) {
  const newName = prompt("Enter new filename:", currentName);
  if (!newName || newName.trim() === "" || newName.trim() === currentName) return;

  try {
    const response = await fetch(`/api/documents/${id}/rename`, {
      method: "PUT",
      headers: getAuthHeaders(),
      body: JSON.stringify({ filename: newName.trim() })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to rename document.");
    }

    showToast("File renamed successfully.", "success");
    loadDashboardData();
    fetchAndPopulateSidebarDocs(); // Refresh sidebar selector list
  } catch (err) {
    showToast(err.message, "danger");
  }
}

async function deleteDocument(id) {
  if (!confirm("Are you sure you want to delete this document? This will erase all its page chunks, FAISS vector indices, chat sessions, summaries, flashcards, and quizzes. This cannot be undone.")) return;

  try {
    const response = await fetch(`/api/documents/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders()
    });

    if (!response.ok) throw new Error("Failed to delete document.");

    showToast("Document deleted successfully.", "success");
    
    // Clear active selection if the active file was deleted
    if (Number(activeDocumentId) === Number(id)) {
      activeDocumentId = null;
      localStorage.removeItem("active_document_id");
    }

    loadDashboardData();
    fetchAndPopulateSidebarDocs();
  } catch (err) {
    showToast(err.message, "danger");
  }
}

// Centralized Authentication Utilities

// Global API Interceptor for Vercel deployment pointing to local backend
const LOCAL_BACKEND = "http://localhost:8000";
const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

if (!isLocalhost) {
  // Monkey-patch window.fetch
  const originalFetch = window.fetch;
  window.fetch = function (input, init) {
    if (typeof input === "string" && input.startsWith("/api")) {
      input = LOCAL_BACKEND + input;
    }
    return originalFetch(input, init);
  };

  // Monkey-patch XMLHttpRequest
  const originalOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (method, url, async, user, password) {
    if (typeof url === "string" && url.startsWith("/api")) {
      url = LOCAL_BACKEND + url;
    }
    return originalOpen.apply(this, arguments);
  };
}

const AUTH_TOKEN_KEY = "ai_research_token";
const USER_INFO_KEY = "ai_research_user";

// Get base API URL (handles production/staging relative or absolute configurations)
const API_BASE_URL = isLocalhost ? window.location.origin : LOCAL_BACKEND;

/**
 * Checks if the user is authenticated.
 */
function isAuthenticated() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (!token) return false;
  
  // Basic JWT expiration check
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000; // convert to ms
    if (Date.now() >= exp) {
      logout();
      return false;
    }
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Returns authorization headers for fetch requests.
 */
function getAuthHeaders() {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  return {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${token}`
  };
}

/**
 * Saves login token and metadata.
 */
function saveSession(token, username, email) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(USER_INFO_KEY, JSON.stringify({ username, email }));
}

/**
 * Clear session and redirect to login page.
 */
function logout() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(USER_INFO_KEY);
  window.location.href = "/login.html";
}

/**
 * Route protection: Call at the top of pages that require login.
 */
function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = "/login.html";
  }
}

/**
 * Route protection: Call at the top of pages that should NOT be visible to logged in users (e.g. login/signup).
 */
function requireGuest() {
  if (isAuthenticated()) {
    window.location.href = "/dashboard.html";
  }
}

/**
 * Helper to display toast notifications.
 */
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type} animate-slideup`;
  
  // Custom icons based on types
  let icon = "";
  if (type === "success") {
    icon = `<svg viewBox="0 0 24 24" width="20" height="20" stroke="var(--success)" stroke-width="2" fill="none"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`;
  } else if (type === "danger") {
    icon = `<svg viewBox="0 0 24 24" width="20" height="20" stroke="var(--danger)" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
  } else {
    icon = `<svg viewBox="0 0 24 24" width="20" height="20" stroke="var(--primary)" stroke-width="2" fill="none"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
  }

  toast.innerHTML = `
    ${icon}
    <span>${message}</span>
  `;
  container.appendChild(toast);

  // Auto-remove toast after 4 seconds
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(10px)";
    toast.style.transition = "opacity 0.3s, transform 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

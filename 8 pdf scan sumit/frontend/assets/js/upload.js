// PDF upload and collection workspace actions

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");

  if (!dropZone || !fileInput) return;

  // Click zone triggers selector
  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFilesUpload(files);
    }
  });

  // Drag and Drop events
  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    }, false);
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFilesUpload(files);
    }
  });

  // Initial load of uploads list
  loadUploadsCollection();
});

/**
 * Handle queue of multiple files if uploaded
 */
function handleFilesUpload(files) {
  Array.from(files).forEach(file => {
    if (file.type !== "application/pdf" && !file.name.endsWith(".pdf")) {
      showToast(`'${file.name}' is not a PDF file.`, "danger");
      return;
    }
    
    const maxLimit = 100 * 1024 * 1024; // 100MB
    if (file.size > maxLimit) {
      showToast(`'${file.name}' exceeds the 100MB limit.`, "danger");
      return;
    }

    uploadSingleFile(file);
  });
}

/**
 * Uploads a single file using XMLHttpRequest to track progress
 */
function uploadSingleFile(file) {
  const progressList = document.getElementById("progress-list");
  if (!progressList) return;

  // Create unique ID for progress item
  const cardId = "upload_" + Date.now() + "_" + Math.floor(Math.random() * 1000);
  
  // Render progress card
  const progressCard = document.createElement("div");
  progressCard.id = cardId;
  progressCard.className = "progress-card animate-slideup";
  progressCard.innerHTML = `
    <div class="progress-card-info">
      <span class="progress-filename" title="${file.name}">${file.name}</span>
      <span class="progress-status" id="${cardId}_status">Uploading (0%)</span>
    </div>
    <div class="progress-bar-bg">
      <div class="progress-bar-fill" id="${cardId}_fill" style="width: 0%;"></div>
    </div>
  `;
  progressList.appendChild(progressCard);

  // Setup XHR request
  const xhr = new XMLHttpRequest();
  const formData = new FormData();
  formData.append("file", file);

  xhr.open("POST", "/api/upload");
  
  // Set Auth headers
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
  }

  // Upload Progress
  xhr.upload.addEventListener("progress", (e) => {
    if (e.lengthComputable) {
      const percent = Math.round((e.loaded / e.total) * 100);
      const statusText = document.getElementById(`${cardId}_status`);
      const fillBar = document.getElementById(`${cardId}_fill`);
      
      if (percent < 100) {
        if (statusText) statusText.innerText = `Uploading (${percent}%)`;
        if (fillBar) fillBar.style.width = `${percent}%`;
      } else {
        if (statusText) statusText.innerText = "Analyzing & Vector Indexing...";
        if (fillBar) {
          fillBar.style.width = "100%";
          fillBar.style.backgroundColor = "var(--primary)";
        }
      }
    }
  });

  // Upload Completion Callback
  xhr.onreadystatechange = () => {
    if (xhr.readyState === XMLHttpRequest.DONE) {
      const statusText = document.getElementById(`${cardId}_status`);
      const fillBar = document.getElementById(`${cardId}_fill`);

      if (xhr.status === 200 || xhr.status === 201) {
        try {
          const res = JSON.parse(xhr.responseText);
          
          if (statusText) {
            statusText.innerText = "Completed & Indexed!";
            statusText.style.color = "var(--success)";
          }
          if (fillBar) fillBar.style.backgroundColor = "var(--success)";
          
          showToast(`'${file.name}' processed successfully.`, "success");
          
          // Set as active document
          localStorage.setItem("active_document_id", res.id);
          
          // Reload view lists
          loadUploadsCollection();
          fetchAndPopulateSidebarDocs();

          // Auto-remove progress card after 3 seconds
          setTimeout(() => {
            progressCard.style.opacity = "0";
            progressCard.style.transform = "translateY(-10px)";
            progressCard.style.transition = "opacity 0.5s, transform 0.5s";
            setTimeout(() => progressCard.remove(), 500);
          }, 3000);

        } catch (e) {
          handleUploadError(cardId, "Upload succeeded, but could not parse response details.");
        }
      } else {
        // Retrieve error message details
        let errMsg = "Upload failed.";
        try {
          const errRes = JSON.parse(xhr.responseText);
          errMsg = errRes.detail || errMsg;
        } catch (e) {}
        
        handleUploadError(cardId, errMsg);
      }
    }
  };

  xhr.send(formData);
}

function handleUploadError(cardId, message) {
  const statusText = document.getElementById(`${cardId}_status`);
  const fillBar = document.getElementById(`${cardId}_fill`);

  if (statusText) {
    statusText.innerText = message;
    statusText.style.color = "var(--danger)";
  }
  if (fillBar) {
    fillBar.style.width = "100%";
    fillBar.style.backgroundColor = "var(--danger)";
  }
  
  showToast(message, "danger");
}

/**
 * Loads uploaded files in the Upload Page table
 */
async function loadUploadsCollection() {
  const tableBody = document.getElementById("upload-table-body");
  if (!tableBody) return;

  try {
    const response = await fetch('/api/documents', {
      headers: getAuthHeaders()
    });

    if (!response.ok) throw new Error("Failed to load your library collection.");

    const docs = await response.json();
    
    if (docs.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="4" style="text-align: center; color: var(--text-tertiary); padding: 3rem 1rem;">
            No documents uploaded yet. Drag and drop a file above.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = "";
    docs.forEach(doc => {
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
            <button class="action-btn" onclick="renameDocumentInUploads(${doc.id}, '${doc.filename}')" title="Rename file">
              <svg viewBox="0 0 24 24" stroke-width="2" fill="none">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4z"/>
              </svg>
            </button>
            <button class="action-btn action-btn-delete" onclick="deleteDocumentInUploads(${doc.id})" title="Delete file">
              <svg viewBox="0 0 24 24" stroke-width="2" fill="none">
                <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </td>
      `;
      tableBody.appendChild(tr);
    });

  } catch (err) {
    showToast(err.message, "danger");
  }
}

// Wrapper controls to synchronize updates across view controllers
function renameDocumentInUploads(id, currentName) {
  renameDocument(id, currentName).then(() => {
    loadUploadsCollection();
  });
}

function deleteDocumentInUploads(id) {
  deleteDocument(id).then(() => {
    loadUploadsCollection();
  });
}

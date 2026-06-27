// Summaries, MCQ Quizzes, and Flashcards client controller

// MCQ Game State variables
let quizQuestions = [];
let quizCurrentIndex = 0;
let quizScore = 0;
let quizTimerInterval = null;
let quizSecondsLeft = 0;
let quizSelectedOption = null;
let quizIsAnswered = false;

// Flashcards State variables
let flashcardsDeck = [];
let flashcardsIndex = 0;

// Hook triggered by app.js when active document selection changes
function onActiveDocumentChange(docId) {
  const isSummaryPage = window.location.pathname.includes("summary.html");
  const isMCQPage = window.location.pathname.includes("mcq.html");
  const isFlashcardPage = window.location.pathname.includes("flashcards.html");

  const actionHeaders = document.querySelector(".header-actions");
  const workspaceArea = document.getElementById(
    isSummaryPage ? "summary-workspace-area" : 
    isMCQPage ? "quiz-workspace-area" : "cards-workspace-area"
  );
  const noDocWarning = document.getElementById("no-doc-warning");
  const docTitle = document.getElementById("active-doc-title");
  const docSubtitle = document.getElementById("active-doc-subtitle");

  if (!docId) {
    if (actionHeaders) actionHeaders.style.display = "none";
    if (workspaceArea) workspaceArea.style.display = "none";
    if (noDocWarning) noDocWarning.style.display = "flex";
    if (docTitle) docTitle.innerText = "Study Assistant";
    if (docSubtitle) docSubtitle.innerText = "Please select a PDF file from the sidebar selector to start studying.";
    resetQuizState();
    return;
  }

  // Get filename from global lists
  const activeDoc = globalDocuments.find(d => Number(d.id) === Number(docId));
  const filename = activeDoc ? activeDoc.filename : "Selected Document";

  if (docTitle) docTitle.innerText = filename;
  
  if (actionHeaders) actionHeaders.style.display = "flex";
  if (workspaceArea) workspaceArea.style.display = "block";
  if (noDocWarning) noDocWarning.style.display = "none";

  // Check page context and load previous summaries/questions/flashcards
  if (isSummaryPage) {
    docSubtitle.innerText = "AI summaries and concept keywords.";
    loadExistingSummary(docId);
  } else if (isMCQPage) {
    docSubtitle.innerText = "Configure and take multiple choice quizzes.";
    resetQuizPlayfield();
    loadExistingQuiz(docId);
  } else if (isFlashcardPage) {
    docSubtitle.innerText = "Study interactive flashcards to test memory.";
    resetFlashcardsPlayfield();
    loadExistingFlashcards(docId);
  }
}

// --- SUMMARY WORKSPACE CODE ---

async function loadExistingSummary(docId) {
  // Try retrieving cached summary from database
  const loading = document.getElementById("summary-loading");
  const initialPrompt = document.getElementById("tab-short");
  
  try {
    if (loading) loading.style.display = "block";
    if (initialPrompt) initialPrompt.style.display = "none";
    
    const response = await fetch("/api/summary", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ document_id: Number(docId), force_regenerate: false })
    });

    if (loading) loading.style.display = "none";

    if (response.ok) {
      const data = await response.json();
      renderSummaryUI(data.summary, data.keywords);
    } else {
      // If none generated, revert to initial prompt
      if (initialPrompt) {
        initialPrompt.style.display = "block";
        initialPrompt.innerHTML = `<p style="color: var(--text-tertiary);">Click the <strong>Generate AI Summary</strong> button above to compile study guides.</p>`;
      }
    }
  } catch (err) {
    if (loading) loading.style.display = "none";
    console.error("Cache load failed: ", err);
  }
}

async function generateSummary() {
  const docId = localStorage.getItem("active_document_id");
  if (!docId) return;

  const generateBtn = document.getElementById("generate-summary-btn");
  const loading = document.getElementById("summary-loading");
  const tabContents = document.querySelectorAll(".summary-tab-content");

  // Disable buttons & show loading
  generateBtn.disabled = true;
  generateBtn.innerText = "Generating...";
  if (loading) loading.style.display = "block";
  tabContents.forEach(tc => tc.style.display = "none");

  try {
    const response = await fetch("/api/summary", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ document_id: Number(docId), force_regenerate: true })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Summary generation failed.");
    }

    const data = await response.json();
    renderSummaryUI(data.summary, data.keywords);
    showToast("AI Summary generated successfully!", "success");

  } catch (err) {
    showToast(err.message, "danger");
    // Reset initial tab
    const initialPrompt = document.getElementById("tab-short");
    if (initialPrompt) {
      initialPrompt.style.display = "block";
      initialPrompt.innerHTML = `<p style="color: var(--danger);">${err.message}. Try generating again.</p>`;
    }
  } finally {
    if (loading) loading.style.display = "none";
    generateBtn.disabled = false;
    generateBtn.innerText = "Generate AI Summary";
  }
}

function renderSummaryUI(summary, keywords) {
  // Populate summaries tabs
  document.getElementById("tab-short").innerHTML = `<p>${summary.short}</p>`;
  
  // Format body text
  document.getElementById("tab-medium").innerHTML = summary.medium.split("\n\n").map(p => `<p>${p}</p>`).join("");
  document.getElementById("tab-detailed").innerHTML = summary.detailed.split("\n\n").map(p => `<p>${p}</p>`).join("");
  
  document.getElementById("tab-bullets").innerHTML = `<ul>` + summary.bullets.map(b => `<li>${b}</li>`).join("") + `</ul>`;
  
  // Chapter list
  document.getElementById("tab-chapter").innerHTML = `<ul>` + summary.chapter_wise.map(c => `<li>${c}</li>`).join("") + `</ul>`;
  
  document.getElementById("tab-simple").innerHTML = `<p>${summary.simple_language}</p>`;
  document.getElementById("tab-revision").innerHTML = summary.revision.split("\n\n").map(p => `<p>${p}</p>`).join("");

  // Switch to short tab initially
  const firstTabLink = document.querySelector(".summary-tabs-nav .tab-link");
  if (firstTabLink) switchSummaryTab(firstTabLink, "tab-short");

  // Populate concept keywords grid
  const grid = document.getElementById("keywords-grid-box");
  if (!grid) return;

  grid.innerHTML = "";
  if (!keywords || keywords.length === 0) {
    grid.innerHTML = `<p style="color: var(--text-tertiary); padding: 1rem;">No explicit concept tags extracted.</p>`;
    return;
  }

  keywords.forEach(kw => {
    const card = document.createElement("div");
    card.className = "keyword-card";
    const typeLabel = kw.type || "Concept";
    const typeClass = typeLabel.toLowerCase().replace(" ", "_");

    card.innerHTML = `
      <div class="keyword-header">
        <span class="keyword-title">${kw.term}</span>
        <span class="keyword-type-badge keyword-type-${typeClass}">${typeLabel}</span>
      </div>
      <p class="keyword-desc">${kw.definition}</p>
    `;
    grid.appendChild(card);
  });
}

function switchSummaryTab(element, tabId) {
  // Toggle tab link headers
  const links = document.querySelectorAll(".summary-tabs-nav .tab-link");
  links.forEach(l => l.classList.remove("active"));
  element.classList.add("active");

  // Toggle tab content panes
  const contents = document.querySelectorAll(".summary-tab-content");
  contents.forEach(c => c.classList.remove("active"));
  
  const activeContent = document.getElementById(tabId);
  if (activeContent) activeContent.classList.add("active");
}


// --- MCQ WORKSPACE QUIZ CODE ---

function resetQuizState() {
  clearInterval(quizTimerInterval);
  quizQuestions = [];
  quizCurrentIndex = 0;
  quizScore = 0;
  quizSelectedOption = null;
  quizIsAnswered = false;
}

function resetQuizPlayfield() {
  resetQuizState();
  document.getElementById("quiz-welcome-panel").style.display = "block";
  document.getElementById("quiz-loading").style.display = "none";
  document.getElementById("quiz-play-field").style.display = "none";
  document.getElementById("quiz-results-panel").style.display = "none";
  document.getElementById("quiz-meta-panel").style.display = "none";
}

async function loadExistingQuiz(docId) {
  const loading = document.getElementById("quiz-loading");
  const welcomePanel = document.getElementById("quiz-welcome-panel");
  const playField = document.getElementById("quiz-play-field");
  
  try {
    if (loading) loading.style.display = "block";
    if (welcomePanel) welcomePanel.style.display = "none";
    
    const response = await fetch("/api/mcq", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        document_id: Number(docId),
        difficulty: "Medium",
        force_regenerate: false
      })
    });
    
    if (loading) loading.style.display = "none";
    
    if (response.ok) {
      const data = await response.json();
      quizQuestions = data.questions;
      if (quizQuestions.length > 0) {
        if (playField) playField.style.display = "block";
        document.getElementById("quiz-meta-panel").style.display = "flex";
        
        // Start count down timer (30 seconds per question)
        quizSecondsLeft = quizQuestions.length * 30;
        startQuizTimer();
        renderMCQQuestion(0);
      } else {
        if (welcomePanel) welcomePanel.style.display = "block";
      }
    } else {
      if (welcomePanel) welcomePanel.style.display = "block";
    }
  } catch (err) {
    if (loading) loading.style.display = "none";
    if (welcomePanel) welcomePanel.style.display = "block";
    console.error("Cache load quiz failed: ", err);
  }
}

function showQuizConfigSelection() {
  resetQuizPlayfield();
}

async function generateQuiz() {
  const docId = localStorage.getItem("active_document_id");
  if (!docId) return;

  resetQuizState();

  const qty = document.getElementById("quiz-qty-select").value;
  const diff = document.getElementById("quiz-diff-select").value;

  const generateBtn = document.getElementById("generate-mcq-btn");
  const welcomePanel = document.getElementById("quiz-welcome-panel");
  const loading = document.getElementById("quiz-loading");
  const resultsPanel = document.getElementById("quiz-results-panel");
  const playField = document.getElementById("quiz-play-field");

  // Toggle Loading states
  generateBtn.disabled = true;
  generateBtn.innerText = "Analyzing...";
  if (welcomePanel) welcomePanel.style.display = "none";
  if (resultsPanel) resultsPanel.style.display = "none";
  if (playField) playField.style.display = "none";
  if (loading) loading.style.display = "block";

  try {
    const response = await fetch("/api/mcq", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        document_id: Number(docId),
        num_questions: Number(qty),
        difficulty: diff,
        force_regenerate: true // Force generate to ensure fresh questions set
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Quiz generation failed.");
    }

    const data = await response.json();
    quizQuestions = data.questions;

    if (quizQuestions.length === 0) {
      throw new Error("No quiz questions returned from service.");
    }

    // Hide loader
    if (loading) loading.style.display = "none";
    
    // Start Quiz play
    playField.style.display = "block";
    document.getElementById("quiz-meta-panel").style.display = "flex";
    
    // Start count down timer (30 seconds per question)
    quizSecondsLeft = quizQuestions.length * 30;
    startQuizTimer();

    renderMCQQuestion(0);
    showToast("Quiz loaded! Go!", "success");

  } catch (err) {
    showToast(err.message, "danger");
    resetQuizPlayfield();
  } finally {
    generateBtn.disabled = false;
    generateBtn.innerText = "Generate Quiz";
  }
}

function startQuizTimer() {
  const display = document.getElementById("timer-display");
  const timerBox = document.getElementById("quiz-timer-box");
  
  if (quizTimerInterval) clearInterval(quizTimerInterval);

  timerBox.classList.remove("danger");

  const updateTimerHTML = () => {
    if (quizSecondsLeft <= 0) {
      clearInterval(quizTimerInterval);
      finishQuizDueToTimeout();
      return;
    }

    if (quizSecondsLeft < 20) {
      timerBox.classList.add("danger");
    }

    const mins = Math.floor(quizSecondsLeft / 60);
    const secs = quizSecondsLeft % 60;
    
    display.innerText = `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    quizSecondsLeft--;
  };

  updateTimerHTML();
  quizTimerInterval = setInterval(updateTimerHTML, 1000);
}

function renderMCQQuestion(idx) {
  quizCurrentIndex = idx;
  quizSelectedOption = null;
  quizIsAnswered = false;

  const item = quizQuestions[idx];
  
  // Progress indicators
  document.getElementById("quiz-progress-text").innerText = `Question ${idx + 1} of ${quizQuestions.length}`;
  document.getElementById("quiz-question-text").innerText = item.question;

  // Options buttons
  const optGroup = document.getElementById("quiz-options-group");
  optGroup.innerHTML = "";

  item.options.forEach(opt => {
    const btn = document.createElement("div");
    btn.className = "quiz-option";
    btn.innerText = opt;
    btn.onclick = () => selectMCQOption(btn, opt);
    optGroup.appendChild(btn);
  });

  // Reset actions
  const nextBtn = document.getElementById("quiz-next-btn");
  nextBtn.innerText = "Submit Answer";
  nextBtn.disabled = true;

  document.getElementById("quiz-explanation-box").style.display = "none";
}

function selectMCQOption(btn, optionValue) {
  if (quizIsAnswered) return; // Locked after submit

  const options = document.querySelectorAll("#quiz-options-group .quiz-option");
  options.forEach(o => o.classList.remove("selected"));

  btn.classList.add("selected");
  quizSelectedOption = optionValue;

  document.getElementById("quiz-next-btn").disabled = false;
}

function submitOrNextQuestion() {
  if (!quizIsAnswered) {
    // 1. Submit Mode
    quizIsAnswered = true;
    const item = quizQuestions[quizCurrentIndex];
    const isCorrect = quizSelectedOption === item.correct_answer;

    if (isCorrect) quizScore++;

    // Add colors to UI options
    const options = document.querySelectorAll("#quiz-options-group .quiz-option");
    options.forEach(btn => {
      btn.classList.remove("selected");
      if (btn.innerText === item.correct_answer) {
        btn.classList.add("correct");
      } else if (btn.innerText === quizSelectedOption) {
        btn.classList.add("incorrect");
      }
    });

    // Render explanation details
    const explanationBox = document.getElementById("quiz-explanation-box");
    document.getElementById("quiz-explanation-text").innerText = item.explanation;
    explanationBox.style.display = "block";

    // Set next actions
    const nextBtn = document.getElementById("quiz-next-btn");
    if (quizCurrentIndex + 1 < quizQuestions.length) {
      nextBtn.innerText = "Next Question";
    } else {
      nextBtn.innerText = "Show Quiz Results";
    }
  } else {
    // 2. Next Mode
    if (quizCurrentIndex + 1 < quizQuestions.length) {
      renderMCQQuestion(quizCurrentIndex + 1);
    } else {
      finishQuizSession();
    }
  }
}

function finishQuizSession() {
  clearInterval(quizTimerInterval);
  document.getElementById("quiz-play-field").style.display = "none";
  document.getElementById("quiz-meta-panel").style.display = "none";
  
  const scoreNum = document.getElementById("results-score-num");
  const headline = document.getElementById("results-headline");
  const desc = document.getElementById("results-desc");

  scoreNum.innerText = `${quizScore}/${quizQuestions.length}`;
  
  const ratio = quizScore / quizQuestions.length;
  if (ratio >= 0.8) {
    headline.innerText = "Mastery Level Achieved!";
    desc.innerText = "Excellent performance! You demonstrate a solid understanding of the document details.";
  } else if (ratio >= 0.5) {
    headline.innerText = "Good Effort!";
    desc.innerText = "You're getting there! Review the concepts and try again to improve your score.";
  } else {
    headline.innerText = "Needs Review";
    desc.innerText = "Study the summaries and keywords definitions in detail before retrying.";
  }

  document.getElementById("quiz-results-panel").style.display = "flex";
}

function finishQuizDueToTimeout() {
  showToast("Time expired!", "warning");
  finishQuizSession();
}

function restartQuiz() {
  resetQuizState();
  if (quizQuestions.length > 0) {
    document.getElementById("quiz-play-field").style.display = "block";
    document.getElementById("quiz-results-panel").style.display = "none";
    document.getElementById("quiz-meta-panel").style.display = "flex";
    
    quizSecondsLeft = quizQuestions.length * 30;
    startQuizTimer();
    renderMCQQuestion(0);
  }
}


// --- FLASHCARDS STUDY WORKSPACE CODE ---

function resetFlashcardsPlayfield() {
  flashcardsDeck = [];
  flashcardsIndex = 0;
  
  document.getElementById("cards-welcome-panel").style.display = "block";
  document.getElementById("cards-loading").style.display = "none";
  document.getElementById("cards-play-field").style.display = "none";
}

async function loadExistingFlashcards(docId) {
  const loading = document.getElementById("cards-loading");
  const welcome = document.getElementById("cards-welcome-panel");
  const playField = document.getElementById("cards-play-field");
  
  try {
    if (loading) loading.style.display = "block";
    if (welcome) welcome.style.display = "none";
    
    const response = await fetch("/api/flashcards", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        document_id: Number(docId),
        difficulty: "Medium",
        force_regenerate: false
      })
    });
    
    if (loading) loading.style.display = "none";
    
    if (response.ok) {
      const data = await response.json();
      flashcardsDeck = data.cards;
      if (flashcardsDeck.length > 0) {
        if (playField) playField.style.display = "block";
        renderFlashcard(0);
      } else {
        if (welcome) welcome.style.display = "block";
      }
    } else {
      if (welcome) welcome.style.display = "block";
    }
  } catch (err) {
    if (loading) loading.style.display = "none";
    if (welcome) welcome.style.display = "block";
    console.error("Cache load flashcards failed: ", err);
  }
}

async function generateFlashcards() {
  const docId = localStorage.getItem("active_document_id");
  if (!docId) return;

  const diff = document.getElementById("cards-diff-select").value;
  const generateBtn = document.getElementById("generate-cards-btn");
  const welcome = document.getElementById("cards-welcome-panel");
  const loading = document.getElementById("cards-loading");
  const playField = document.getElementById("cards-play-field");

  generateBtn.disabled = true;
  generateBtn.innerText = "Analyzing...";
  if (welcome) welcome.style.display = "none";
  if (playField) playField.style.display = "none";
  if (loading) loading.style.display = "block";

  try {
    const response = await fetch("/api/flashcards", {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({
        document_id: Number(docId),
        difficulty: diff,
        force_regenerate: true
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Flashcards generation failed.");
    }

    const data = await response.json();
    flashcardsDeck = data.cards;

    if (flashcardsDeck.length === 0) {
      throw new Error("No flashcard items generated.");
    }

    if (loading) loading.style.display = "none";
    
    // Play flashcards
    playField.style.display = "block";
    renderFlashcard(0);
    showToast("Study deck loaded!", "success");

  } catch (err) {
    showToast(err.message, "danger");
    resetFlashcardsPlayfield();
  } finally {
    generateBtn.disabled = false;
    generateBtn.innerText = "Generate Deck";
  }
}

function renderFlashcard(idx) {
  flashcardsIndex = idx;
  const card = flashcardsDeck[idx];

  // Remove flipped styling to show front initially
  const cardEl = document.getElementById("interactive-card");
  if (cardEl) cardEl.classList.remove("flipped");

  document.getElementById("card-front-text").innerText = card.front;
  document.getElementById("card-back-text").innerText = card.back;
  
  // Progress indicators
  document.getElementById("card-count-text").innerText = `Card ${idx + 1} of ${flashcardsDeck.length}`;

  // Disable button edges
  document.getElementById("card-prev-btn").disabled = idx === 0;
  document.getElementById("card-next-btn").disabled = idx === flashcardsDeck.length - 1;
}

function flipActiveCard() {
  const cardEl = document.getElementById("interactive-card");
  if (cardEl) {
    cardEl.classList.toggle("flipped");
  }
}

function navigateCard(step) {
  const target = flashcardsIndex + step;
  if (target >= 0 && target < flashcardsDeck.length) {
    renderFlashcard(target);
  }
}

function shuffleCardDeck() {
  if (flashcardsDeck.length <= 1) return;

  // Fisher-Yates shuffle
  for (let i = flashcardsDeck.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [flashcardsDeck[i], flashcardsDeck[j]] = [flashcardsDeck[j], flashcardsDeck[i]];
  }

  showToast("Study deck shuffled!", "success");
  renderFlashcard(0);
}


// --- SECURE DOWNLOAD EXPORTS MODULE ---

async function triggerDownload(type) {
  const docId = localStorage.getItem("active_document_id");
  if (!docId) {
    showToast("Please select a document first.", "warning");
    return;
  }

  try {
    showToast("Building file for download...", "info");
    
    // Fetch file with JWT token headers
    const response = await fetch(`/api/download/${type}/${docId}`, {
      headers: getAuthHeaders()
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to download study resource.");
    }

    // Convert response to raw blob bytes
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    
    // Virtual anchor trigger click download
    const a = document.createElement("a");
    a.href = url;
    
    // Try resolving filename from content disposition headers
    let downloadFilename = `study_material_${type}.md`;
    const disposition = response.headers.get("content-disposition");
    if (disposition && disposition.indexOf("attachment") !== -1) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
      const matches = filenameRegex.exec(disposition);
      if (matches !== null && matches[1]) {
        downloadFilename = matches[1].replace(/['"]/g, "");
      }
    }

    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup reference URLs
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    showToast("Download started successfully.", "success");

  } catch (err) {
    showToast(err.message, "danger");
  }
}

// Trigger initial load hooks
window.addEventListener("load", () => {
  const activeDocId = localStorage.getItem("active_document_id");
  onActiveDocumentChange(activeDocId);
});

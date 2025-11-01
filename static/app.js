/* ============================================
   PROJECT SAMARTH - ENHANCED JAVASCRIPT
   ============================================ */

let sessionId = null;

// === SESSION MANAGEMENT ===
async function createSession() {
    try {
        const response = await fetch('/api/session/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        sessionId = data.session_id;
        console.log('✓ Session created:', sessionId);
    } catch (error) {
        console.error('✗ Error creating session:', error);
        showNotification('Failed to create session', 'error');
    }
}

// === MESSAGE HANDLING ===
function addMessage(content, role) {
    const messagesContainer = document.getElementById('chatMessages');
    
    // Remove welcome screen if it exists
    const welcomeScreen = messagesContainer.querySelector('.welcome-screen');
    if (welcomeScreen) {
        welcomeScreen.style.opacity = '0';
        setTimeout(() => welcomeScreen.remove(), 300);
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    messageDiv.style.opacity = '0';
    
    const headerDiv = document.createElement('div');
    headerDiv.className = 'message-header';
    
    const avatarDiv = document.createElement('div');
    avatarDiv.className = 'message-avatar';
    avatarDiv.textContent = role === 'user' ? 'You' : 'AI';
    
    const labelDiv = document.createElement('div');
    labelDiv.className = 'message-label';
    labelDiv.textContent = role === 'user' ? 'You' : 'Project Samarth';
    
    headerDiv.appendChild(avatarDiv);
    headerDiv.appendChild(labelDiv);
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'assistant') {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }
    
    messageDiv.appendChild(headerDiv);
    messageDiv.appendChild(contentDiv);
    messagesContainer.appendChild(messageDiv);
    
    // Fade in animation
    requestAnimationFrame(() => {
        messageDiv.style.opacity = '1';
    });
    
    // Smooth scroll to bottom
    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
    });
}

function showLoadingMessage() {
    const messagesContainer = document.getElementById('chatMessages');
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.id = 'loadingIndicator';
    loadingDiv.textContent = 'Analyzing data and generating insights...';
    messagesContainer.appendChild(loadingDiv);
    messagesContainer.scrollTo({
        top: messagesContainer.scrollHeight,
        behavior: 'smooth'
    });
}

function removeLoadingMessage() {
    const loading = document.getElementById('loadingIndicator');
    if (loading) {
        loading.style.opacity = '0';
        setTimeout(() => loading.remove(), 300);
    }
}

// === SOURCES DISPLAY ===
function displaySources(sources) {
    const sourcesContainer = document.getElementById('sourcesContainer');
    
    if (!sources || sources.length === 0) {
        sourcesContainer.innerHTML = `
            <div class="placeholder-state">
                <div class="placeholder-icon">📄</div>
                <p>No sources available</p>
            </div>
        `;
        return;
    }
    
    sourcesContainer.innerHTML = '';
    
    sources.forEach((source, index) => {
        const sourceDiv = document.createElement('div');
        sourceDiv.className = 'source-item';
        sourceDiv.style.animationDelay = `${index * 0.1}s`;
        
        sourceDiv.innerHTML = `
            <div class="source-name">${index + 1}. ${source.dataset_name}</div>
            <div class="source-category">${source.category}</div>
        `;
        
        sourcesContainer.appendChild(sourceDiv);
    });
}

// === PIPELINE INFO DISPLAY ===
function displayPipelineInfo(pipelineInfo) {
    const pipelineContainer = document.getElementById('pipelineInfo');
    
    if (!pipelineInfo) {
        pipelineContainer.innerHTML = `
            <div class="placeholder-state">
                <div class="placeholder-icon">⏳</div>
                <p>Processing info will appear here</p>
            </div>
        `;
        return;
    }
    
    pipelineContainer.innerHTML = '';
    
    const stats = [
        { label: 'Query Variations', value: pipelineInfo.query_variations || 0 },
        { label: 'Retrieved Docs', value: pipelineInfo.retrieved_count || 0 },
        { label: 'After Reranking', value: pipelineInfo.reranked_count || 0 },
        { label: 'Final Context', value: pipelineInfo.final_context_count || 0 }
    ];
    
    stats.forEach((stat, index) => {
        const statDiv = document.createElement('div');
        statDiv.className = 'stat-item';
        statDiv.style.animationDelay = `${index * 0.05}s`;
        statDiv.innerHTML = `
            <div class="stat-label">${stat.label}</div>
            <div class="stat-value">${stat.value}</div>
        `;
        pipelineContainer.appendChild(statDiv);
    });
    
    // Add entities if available
    if (pipelineInfo.entities_found) {
        const entities = pipelineInfo.entities_found;
        const entityParts = [];
        
        if (entities.crops?.length) entityParts.push(`${entities.crops.length} crops`);
        if (entities.states?.length) entityParts.push(`${entities.states.length} states`);
        if (entities.metrics?.length) entityParts.push(`${entities.metrics.length} metrics`);
        
        if (entityParts.length > 0) {
            const entityDiv = document.createElement('div');
            entityDiv.className = 'stat-item';
            entityDiv.innerHTML = `
                <div class="stat-label">Entities Detected</div>
                <div class="stat-value">${entityParts.join(', ')}</div>
            `;
            pipelineContainer.appendChild(entityDiv);
        }
    }
}

// === SEND QUESTION ===
async function sendQuestion(question) {
    const sendBtn = document.getElementById('sendBtn');
    const questionInput = document.getElementById('questionInput');
    
    // Disable input
    sendBtn.disabled = true;
    questionInput.disabled = true;
    
    // Add user message
    addMessage(question, 'user');
    
    // Clear input
    questionInput.value = '';
    resetTextareaHeight();
    
    // Show loading
    showLoadingMessage();
    updatePipelineStatus('processing');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        removeLoadingMessage();
        
        if (data.error) {
            addMessage(`⚠️ Error: ${data.error}`, 'assistant');
            updatePipelineStatus('error');
        } else {
            addMessage(data.answer, 'assistant');
            displaySources(data.sources);
            if (data.pipeline_info) {
                displayPipelineInfo(data.pipeline_info);
            }
        }
    } catch (error) {
        removeLoadingMessage();
        addMessage(`⚠️ Network error: ${error.message}`, 'assistant');
        updatePipelineStatus('error');
        console.error('Error:', error);
    } finally {
        sendBtn.disabled = false;
        questionInput.disabled = false;
        questionInput.focus();
    }
}

// === HELPER FUNCTIONS ===
function updatePipelineStatus(status) {
    const pipelineContainer = document.getElementById('pipelineInfo');
    
    if (status === 'processing') {
        pipelineContainer.innerHTML = `
            <div class="placeholder-state">
                <div class="placeholder-icon">⚙️</div>
                <p>Processing your query...</p>
            </div>
        `;
    } else if (status === 'error') {
        pipelineContainer.innerHTML = `
            <div class="placeholder-state">
                <div class="placeholder-icon">⚠️</div>
                <p>Error occurred</p>
            </div>
        `;
    }
}

function clearChat() {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = `
        <div class="welcome-screen">
            <div class="welcome-icon">👋</div>
            <h2>Welcome to Project Samarth</h2>
            <p class="welcome-subtitle">Your intelligent assistant for agricultural and climate data insights</p>
            <div class="feature-pills">
                <span class="pill">🔍 Query Enhancement</span>
                <span class="pill">🎯 Multi-Stage Retrieval</span>
                <span class="pill">⚡ Intelligent Reranking</span>
                <span class="pill">📦 Context Compression</span>
            </div>
            <p class="welcome-prompt">Ask me anything about crop production, rainfall patterns, climate trends, and agricultural insights across India.</p>
        </div>
    `;
    
    // Reset info panels
    document.getElementById('sourcesContainer').innerHTML = `
        <div class="placeholder-state">
            <div class="placeholder-icon">📄</div>
            <p>Sources will appear after your query</p>
        </div>
    `;
    
    document.getElementById('pipelineInfo').innerHTML = `
        <div class="placeholder-state">
            <div class="placeholder-icon">⏳</div>
            <p>Processing information will appear here</p>
        </div>
    `;
    
    createSession();
}

function resetTextareaHeight() {
    const textarea = document.getElementById('questionInput');
    textarea.style.height = 'auto';
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function showNotification(message, type) {
    console.log(`${type.toUpperCase()}: ${message}`);
}

// === UPDATE INPUT SECTION POSITION ===
function updateInputSectionPosition() {
    const leftSidebar = document.getElementById('leftSidebar');
    const rightSidebar = document.getElementById('rightSidebar');
    const inputSection = document.querySelector('.input-section');
    
    if (!inputSection) return;
    
    let leftOffset = 300;
    let rightOffset = 320;
    
    // Check if sidebars are collapsed
    if (leftSidebar && leftSidebar.classList.contains('collapsed')) {
        leftOffset = 0;
    }
    
    if (rightSidebar && rightSidebar.classList.contains('collapsed')) {
        rightOffset = 0;
    }
    
    // Check for responsive breakpoint
    if (window.innerWidth <= 1400) {
        leftOffset = leftSidebar && leftSidebar.classList.contains('collapsed') ? 0 : 280;
        rightOffset = rightSidebar && rightSidebar.classList.contains('collapsed') ? 0 : 300;
    }
    
    if (window.innerWidth <= 1200) {
        leftOffset = leftSidebar && leftSidebar.classList.contains('collapsed') ? 0 : 260;
        rightOffset = rightSidebar && rightSidebar.classList.contains('collapsed') ? 0 : 280;
    }
    
    if (window.innerWidth <= 1024) {
        leftOffset = 0;
        rightOffset = 0;
    }
    
    inputSection.style.left = leftOffset + 'px';
    inputSection.style.right = rightOffset + 'px';
}

// === SIDEBAR TOGGLE ===
function setupSidebarToggles() {
    const leftSidebar = document.getElementById('leftSidebar');
    const rightSidebar = document.getElementById('rightSidebar');
    const leftCollapseBtn = document.getElementById('leftCollapseBtn');
    const rightCollapseBtn = document.getElementById('rightCollapseBtn');
    
    if (leftCollapseBtn) {
        leftCollapseBtn.addEventListener('click', () => {
            if (leftSidebar) {
                leftSidebar.classList.toggle('collapsed');
                leftCollapseBtn.textContent = leftSidebar.classList.contains('collapsed') ? '▶' : '◀';
                updateInputSectionPosition();
            }
        });
    }
    
    if (rightCollapseBtn) {
        rightCollapseBtn.addEventListener('click', () => {
            if (rightSidebar) {
                rightSidebar.classList.toggle('collapsed');
                rightCollapseBtn.textContent = rightSidebar.classList.contains('collapsed') ? '◀' : '▶';
                updateInputSectionPosition();
            }
        });
    }
}

// === INITIALIZATION ===
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Project Samarth...');
    
    // Create session
    createSession();
    
    // Get elements
    const sendBtn = document.getElementById('sendBtn');
    const questionInput = document.getElementById('questionInput');
    const newChatBtn = document.getElementById('newChatBtn');
    const exampleCards = document.querySelectorAll('.example-card');
    
    // Setup sidebar toggles
    setupSidebarToggles();
    
    // Update input position on window resize
    window.addEventListener('resize', updateInputSectionPosition);
    
    // Initial position update
    updateInputSectionPosition();
    
    // Send button click
    if (sendBtn) {
        sendBtn.addEventListener('click', () => {
            const question = questionInput.value.trim();
            if (question) {
                sendQuestion(question);
            }
        });
    }
    
    // Enter key to send (Shift+Enter for new line)
    if (questionInput) {
        questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const question = questionInput.value.trim();
                if (question) {
                    sendQuestion(question);
                }
            }
        });
        
        // Auto-resize textarea
        questionInput.addEventListener('input', () => {
            autoResizeTextarea(questionInput);
        });
        
        // Focus input on load
        questionInput.focus();
    }
    
    // New chat button
    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            if (confirm('Start a new conversation? Current chat will be cleared.')) {
                clearChat();
            }
        });
    }
    
    // Example cards
    exampleCards.forEach(card => {
        card.addEventListener('click', function() {
            const text = this.querySelector('.example-text').textContent;
            if (questionInput) {
                questionInput.value = text;
                autoResizeTextarea(questionInput);
                questionInput.focus();
                
                // Smooth scroll to input
                questionInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    });
    
    console.log('✓ Project Samarth initialized successfully!');
});
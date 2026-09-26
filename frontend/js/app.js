/**
 * UMILY PERSONAL ASSISTANT — Frontend Logic
 *
 * Handles chat conversation, sticky command bar, real-time Live Activity panel,
 * and confirmation approval/denial workflows connected to FastAPI.
 */

(() => {
    'use strict';

    // Config
    const API_BASE = '/api';
    const STATUS_POLL_MS = 3000;
    const TASK_POLL_MS = 3000;

    // DOM References
    const $ = (sel) => document.querySelector(sel);

    // Header & Status
    const statusDot = $('#status-dot');
    const statusText = $('#status-text');

    // Chat
    const chatHistory = $('#chat-history');
    const welcomeContainer = $('#welcome-container');
    const commandInput = $('#command-input');
    const btnSend = $('#btn-send');
    const btnSendLabel = $('#btn-send-label');

    // Activity Panel
    const taskBadge = $('#activity-task-badge');
    const taskCommand = $('#activity-task-command');
    const liveTimeline = $('#live-timeline');
    const timelineEmptyMsg = $('#timeline-empty-msg');
    const taskResultBox = $('#task-result-box');

    // Confirmation Card
    const confirmationCard = $('#confirmation-card');
    const confirmCardDesc = $('#confirm-card-desc');
    const confirmCardDetails = $('#confirm-card-details');
    const btnCardAllow = $('#btn-card-allow');
    const btnCardDeny = $('#btn-card-deny');

    // History Modal
    const btnToggleHistory = $('#btn-toggle-history');
    const historyModalOverlay = $('#history-modal-overlay');
    const btnCloseHistory = $('#btn-close-history');
    const historyModalList = $('#history-modal-list');

    // State
    let activeTaskId = null;
    let isSending = false;
    let taskPollTimer = null;

    // Helper
    function escapeHTML(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // =========================================================================
    // API Helpers
    // =========================================================================
    async function apiGet(path) {
        const res = await fetch(`${API_BASE}${path}`);
        if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
        return res.json();
    }

    async function apiPost(path, body = {}) {
        const res = await fetch(`${API_BASE}${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
        return res.json();
    }

    // =========================================================================
    // System Status
    // =========================================================================
    async function fetchStatus() {
        try {
            const data = await apiGet('/status');
            updateSystemStatusUI(data);
        } catch {
            setStatusDot('error', 'Disconnected');
        }
    }

    function updateSystemStatusUI(data) {
        if (activeTaskId) return; // Active task status takes precedence

        const stateLabels = {
            idle: ['idle', 'Online'],
            listening_for_command: ['idle', 'Listening…'],
            processing: ['executing', 'Thinking…'],
            executing: ['executing', 'Executing…'],
            waiting_confirmation: ['waiting', 'Waiting for confirmation'],
        };
        const [dotClass, label] = stateLabels[data.assistant_state] || ['idle', 'Online'];
        setStatusDot(dotClass, label);
    }

    function setStatusDot(dotClass, label) {
        statusDot.className = `status-indicator-dot ${dotClass}`;
        statusText.textContent = label;
    }

    // =========================================================================
    // Command Handling & Messaging
    // =========================================================================
    async function sendCommand(overrideText) {
        const text = (overrideText || commandInput.value).trim();
        if (!text || isSending) return;

        isSending = true;
        btnSend.disabled = true;
        btnSendLabel.textContent = '';
        btnSend.insertAdjacentHTML('afterbegin', '<span class="spinner"></span>');
        commandInput.disabled = true;

        // Hide welcome banner on first interaction
        if (welcomeContainer) welcomeContainer.style.display = 'none';

        // Add User Message to Chat
        appendChatMessage('user', text);

        try {
            const data = await apiPost('/command', { command: text });
            activeTaskId = data.task_id;
            
            // Add Assistant Response Message
            appendChatMessage('assistant', data.message || `Processing command: "${text}"`);
            
            commandInput.value = '';
            
            // Update Live Activity Panel
            updateLiveActivity(data);
            
            // Start real-time polling for task progress
            startTaskPolling(data.task_id);

        } catch (err) {
            appendChatMessage('assistant', `Error: Unable to process command. (${err.message})`);
            setStatusDot('error', 'Error');
        } finally {
            isSending = false;
            commandInput.disabled = false;
            commandInput.focus();
            btnSend.disabled = false;
            const spinner = btnSend.querySelector('.spinner');
            if (spinner) spinner.remove();
            btnSendLabel.textContent = '➤';
        }
    }

    function appendChatMessage(sender, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${sender}`;
        
        const senderName = sender === 'user' ? 'You' : 'UMILY';
        msgDiv.innerHTML = `
            <span class="message-sender">${senderName}</span>
            <div class="message-bubble">${escapeHTML(text)}</div>
        `;
        
        chatHistory.appendChild(msgDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    // =========================================================================
    // Live Activity Panel Rendering
    // =========================================================================
    function updateLiveActivity(task) {
        if (!task) return;

        // Update Header Task Info
        taskCommand.textContent = task.command || taskCommand.textContent;
        
        const statusMap = {
            completed: ['completed', 'Completed ✓'],
            failed: ['failed', 'Failed ×'],
            cancelled: ['failed', 'Cancelled'],
            waiting_confirmation: ['waiting', 'Waiting Confirmation !'],
            executing: ['executing', 'Executing…'],
            planning: ['executing', 'Planning…'],
            permission_check: ['executing', 'Checking Permissions…'],
        };
        const [badgeClass, badgeText] = statusMap[task.status] || ['executing', task.status];
        taskBadge.className = `task-status-badge ${badgeClass}`;
        taskBadge.textContent = badgeText;
        setStatusDot(badgeClass, badgeText);

        // Timeline Step Nodes
        renderLiveSteps(task.live_steps || []);

        // Confirmation Card Handling
        if (task.confirmation_required || task.status === 'waiting_confirmation') {
            showConfirmationCard(task);
        } else {
            confirmationCard.style.display = 'none';
        }

        // Result / Failure Summary Box
        if (task.status === 'completed') {
            taskResultBox.style.display = 'block';
            taskResultBox.className = 'task-result-box success';
            taskResultBox.innerHTML = `<strong>✓ TASK COMPLETED</strong><br>${escapeHTML(task.result || 'Command executed successfully.')}`;
            stopTaskPolling();
            activeTaskId = null;
        } else if (task.status === 'failed' || task.status === 'cancelled') {
            taskResultBox.style.display = 'block';
            taskResultBox.className = 'task-result-box error';
            taskResultBox.innerHTML = `<strong>× TASK ${task.status.toUpperCase()}</strong><br>${escapeHTML(task.error || task.result || 'Action was aborted or blocked.')}`;
            stopTaskPolling();
            activeTaskId = null;
        } else {
            taskResultBox.style.display = 'none';
        }
    }

    function renderLiveSteps(steps) {
        if (!steps || steps.length === 0) {
            timelineEmptyMsg.style.display = 'block';
            liveTimeline.innerHTML = '';
            return;
        }

        timelineEmptyMsg.style.display = 'none';
        
        const iconSymbols = {
            completed: '✓',
            executing: '●',
            waiting_confirmation: '!',
            failed: '×',
            blocked: '×',
            pending: '○',
        };

        liveTimeline.innerHTML = steps.map((s, idx) => {
            const status = s.status || 'pending';
            const icon = iconSymbols[status] || '○';
            const tool = s.tool || s.resource_type || 'system';
            const action = s.action || 'step';
            const desc = s.description || `${action} on ${s.resource_name || 'resource'}`;

            return `
                <div class="timeline-step-node">
                    <div class="step-node-icon ${status}">${icon}</div>
                    <div class="step-node-content">
                        <div class="step-node-header">
                            <span class="step-node-title">${escapeHTML(desc)}</span>
                            <span class="step-node-tool">${escapeHTML(tool)}</span>
                        </div>
                        <div class="step-node-desc">Target: <strong>${escapeHTML(s.resource_name || 'system')}</strong></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // =========================================================================
    // Real-Time Task Polling
    // =========================================================================
    let pollCount = 0;
    function startTaskPolling(taskId) {
        stopTaskPolling();
        pollCount = 0;
        taskPollTimer = setInterval(async () => {
            pollCount++;
            try {
                const taskData = await apiGet(`/tasks/${taskId}`);
                updateLiveActivity(taskData);
                if (pollCount > 10 && (taskData.status === 'executing' || taskData.status === 'pending')) {
                    // Safety timeout after 30s
                    stopTaskPolling();
                    activeTaskId = null;
                }
            } catch {
                stopTaskPolling();
                activeTaskId = null;
            }
        }, TASK_POLL_MS);
    }

    function stopTaskPolling() {
        if (taskPollTimer) {
            clearInterval(taskPollTimer);
            taskPollTimer = null;
        }
    }

    // =========================================================================
    // Confirmation Workflows (Allow / Deny)
    // =========================================================================
    function showConfirmationCard(task) {
        confirmationCard.style.display = 'block';
        
        const step = task.pending_step || {};
        const actionName = step.action || 'Execute Step';
        const resourceName = step.resource_name || 'System Resource';
        const resourceType = step.resource_type || 'Action';
        const desc = step.description || task.command || 'Action requires user permission';

        confirmCardDesc.textContent = `Umily is requesting permission to perform an action.`;

        confirmCardDetails.innerHTML = `
            <div class="confirm-row">
                <span class="confirm-row-label">Action</span>
                <span class="confirm-row-val">${escapeHTML(actionName)} (${escapeHTML(resourceType)})</span>
            </div>
            <div class="confirm-row">
                <span class="confirm-row-label">Target</span>
                <span class="confirm-row-val">${escapeHTML(resourceName)}</span>
            </div>
            <div class="confirm-row">
                <span class="confirm-row-label">Description</span>
                <span class="confirm-row-val">${escapeHTML(desc)}</span>
            </div>
        `;

        btnCardAllow.onclick = async () => {
            confirmationCard.style.display = 'none';
            appendChatMessage('assistant', `[User Approved] Resuming task execution…`);
            try {
                const res = await apiPost(`/confirm?task_id=${task.id}`);
                const updated = await apiGet(`/tasks/${task.id}`);
                updateLiveActivity(updated);
                startTaskPolling(task.id);
            } catch (err) {
                appendChatMessage('assistant', `Confirmation error: ${err.message}`);
            }
        };

        btnCardDeny.onclick = async () => {
            confirmationCard.style.display = 'none';
            appendChatMessage('assistant', `[User Denied] Task execution cancelled.`);
            try {
                const res = await apiPost(`/cancel?task_id=${task.id}`);
                const updated = await apiGet(`/tasks/${task.id}`);
                updateLiveActivity(updated);
            } catch (err) {
                appendChatMessage('assistant', `Cancel error: ${err.message}`);
            }
        };
    }

    // =========================================================================
    // History Drawer Modal
    // =========================================================================
    async function loadTaskHistory() {
        try {
            const data = await apiGet('/tasks?limit=20');
            renderHistoryModalList(data.tasks);
        } catch {
            historyModalList.innerHTML = '<div style="color: var(--text-muted); text-align: center;">Unable to load history.</div>';
        }
    }

    function renderHistoryModalList(tasks) {
        if (!tasks || tasks.length === 0) {
            historyModalList.innerHTML = '<div style="color: var(--text-muted); text-align: center;">No task history yet.</div>';
            return;
        }

        historyModalList.innerHTML = tasks.map(t => `
            <div class="history-card">
                <span class="history-card-cmd">#${t.id}: ${escapeHTML(t.command)}</span>
                <span class="task-status-badge ${t.status === 'completed' ? 'completed' : t.status === 'failed' ? 'failed' : 'executing'}">${t.status}</span>
            </div>
        `).join('');
    }

    // =========================================================================
    // Event Listeners
    // =========================================================================
    commandInput.addEventListener('input', () => {
        btnSend.disabled = commandInput.value.trim().length === 0;
    });

    commandInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendCommand();
        }
    });

    btnSend.addEventListener('click', () => sendCommand());

    // Suggestion chips
    document.querySelectorAll('.suggestion-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            const cmd = chip.getAttribute('data-cmd');
            if (cmd) sendCommand(cmd);
        });
    });

    // History Modal events
    btnToggleHistory.addEventListener('click', () => {
        historyModalOverlay.classList.add('active');
        loadTaskHistory();
    });

    btnCloseHistory.addEventListener('click', () => {
        historyModalOverlay.classList.remove('active');
    });

    historyModalOverlay.addEventListener('click', (e) => {
        if (e.target === historyModalOverlay) historyModalOverlay.classList.remove('active');
    });

    // Initial setup
    function init() {
        fetchStatus();
        setInterval(fetchStatus, STATUS_POLL_MS);
        commandInput.focus();
    }

    init();
})();

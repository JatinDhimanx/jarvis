/**
 * J.A.R.V.I.S. Tactical HUD Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
  const coreElement = document.getElementById('reactor-core');
  const stateText = document.getElementById('current-state-text');
  
  const camIndicator = document.getElementById('cam-indicator');
  const camStatus = document.getElementById('cam-status');
  const micIndicator = document.getElementById('mic-indicator');
  const micStatus = document.getElementById('mic-status');
  const netIndicator = document.getElementById('net-indicator');
  const netStatus = document.getElementById('net-status');

  const lastChannel = document.getElementById('last-channel');
  const lastPayload = document.getElementById('last-payload');
  const confidenceBar = document.getElementById('confidence-bar');
  const confidenceVal = document.getElementById('confidence-val');
  const resolvedIntent = document.getElementById('resolved-intent');

  const sysVolume = document.getElementById('sys-volume');
  const sysBrightness = document.getElementById('sys-brightness');
  const sysMemories = document.getElementById('sys-memories');
  const activePlanStatus = document.getElementById('active-plan-status');
  const actionFeed = document.getElementById('action-feed');

  const confirmModal = document.getElementById('confirm-modal');
  const confirmPromptText = document.getElementById('confirm-prompt-text');
  const btnConfirmYes = document.getElementById('btn-confirm-yes');
  const btnConfirmNo = document.getElementById('btn-confirm-no');
  const btnEmergencyStop = document.getElementById('btn-emergency-stop');

  // Emergency stop click
  btnEmergencyStop.addEventListener('click', async () => {
    try {
      await fetch('/api/stop', { method: 'POST' });
    } catch (err) {
      console.error('Failed to trigger emergency stop:', err);
    }
  });

  // Confirmation modal clicks
  btnConfirmYes.addEventListener('click', async () => {
    try {
      await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: true }),
      });
      confirmModal.classList.add('hidden');
    } catch (err) {
      console.error('Failed to send confirmation:', err);
    }
  });

  btnConfirmNo.addEventListener('click', async () => {
    try {
      await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmed: false }),
      });
      confirmModal.classList.add('hidden');
    } catch (err) {
      console.error('Failed to cancel confirmation:', err);
    }
  });

  // Command input submission
  const commandForm = document.getElementById('command-form');
  const commandInput = document.getElementById('command-input');
  const btnSubmitCmd = document.getElementById('btn-submit-cmd');
  const cmdResponseLog = document.getElementById('cmd-response-log');

  function appendCmdLog(text, status, intent) {
    // Remove placeholder if present
    const placeholder = cmdResponseLog.querySelector('.cmd-log-placeholder');
    if (placeholder) placeholder.remove();

    const icon = status === 'success' ? '✅' : status === 'pending_confirmation' ? '⚠️' : '❌';
    const cls  = status === 'success' ? 'log-ok' : status === 'pending_confirmation' ? 'log-warn' : 'log-err';
    const entry = document.createElement('div');
    entry.className = `cmd-log-entry ${cls}`;
    entry.innerHTML = `
      <span class="log-icon">${icon}</span>
      <span class="log-text">${text}</span>
      ${intent ? `<span class="log-intent">[${intent}]</span>` : ''}
      <span class="log-time">${new Date().toLocaleTimeString()}</span>
    `;
    cmdResponseLog.prepend(entry);
    // Keep only last 20 entries
    while (cmdResponseLog.children.length > 20) cmdResponseLog.lastChild.remove();
  }

  if (commandForm) {
    commandForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const text = commandInput.value.trim();
      if (!text) return;

      btnSubmitCmd.disabled = true;
      btnSubmitCmd.textContent = 'ROUTING...';
      try {
        const res = await fetch('/api/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text, channel: 'voice' }),
        });
        const data = await res.json();
        const result = data.result || {};
        const responseText = result.response_text || (res.ok ? 'Command accepted.' : 'Error — no response.');
        const status = result.status || (res.ok ? 'success' : 'error');
        const intent = result.intent || null;
        appendCmdLog(responseText, status, intent);
        commandInput.value = '';
      } catch (err) {
        console.error('Failed to send command:', err);
        appendCmdLog('Network error — could not reach JARVIS.', 'error', null);
      } finally {
        btnSubmitCmd.disabled = false;
        btnSubmitCmd.textContent = 'EXECUTE';
      }
    });
  }

  // Telemetry poll loop
  async function pollStatus() {
    try {
      const response = await fetch('/api/status');
      if (!response.ok) return;
      const data = await response.json();
      updateHUD(data);
    } catch (err) {
      // Offline fallback indicator
      netIndicator.className = 'indicator-badge inactive';
      netStatus.textContent = 'OFFLINE';
    } finally {
      setTimeout(pollStatus, 250);
    }
  }

  function updateHUD(data) {
    // 1. Update State & Core visuals
    const state = (data.state || 'IDLE').toLowerCase();
    stateText.textContent = state.toUpperCase();
    
    // Clear old state-* classes
    coreElement.className = 'reactor-core state-' + state;

    // 2. Privacy indicators
    if (data.camera_active) {
      camIndicator.className = 'indicator-badge active';
      camStatus.textContent = 'ACTIVE';
    } else {
      camIndicator.className = 'indicator-badge inactive';
      camStatus.textContent = 'OFF';
    }

    if (data.mic_active) {
      micIndicator.className = 'indicator-badge active';
      micStatus.textContent = 'LISTENING';
    } else {
      micIndicator.className = 'indicator-badge inactive';
      micStatus.textContent = 'IDLE';
    }

    // Network
    const isOnline = data.system_status && data.system_status.network_online;
    netIndicator.className = isOnline ? 'indicator-badge active' : 'indicator-badge inactive';
    netStatus.textContent = isOnline ? 'ONLINE' : 'OFFLINE';

    // 3. Perception telemetry
    if (data.last_event) {
      lastChannel.textContent = data.last_event.channel.toUpperCase();
      lastPayload.textContent = data.last_event.payload || 'None';
      const conf = data.last_event.confidence || 0;
      confidenceBar.style.width = `${Math.min(100, Math.max(0, conf * 100))}%`;
      confidenceVal.textContent = conf.toFixed(2);
      resolvedIntent.textContent = data.last_event.intent || 'UNKNOWN';
    }

    // 4. System Diagnostics
    if (data.system_status) {
      sysVolume.textContent = `${data.system_status.volume}%`;
      sysBrightness.textContent = `${data.system_status.brightness}%`;
      sysMemories.textContent = `${data.system_status.memory_items} ITEMS`;
    }

    // 5. Active Plan Progress
    if (data.active_plan) {
      activePlanStatus.textContent = `Step ${data.active_plan.current_step + 1} of ${data.active_plan.total_steps}: ${data.active_plan.current_action}`;
    } else {
      activePlanStatus.textContent = 'No active plan';
    }

    // 6. Confirmation Modal
    if (state === 'waiting_confirmation' && data.pending_confirmation) {
      confirmPromptText.textContent = data.pending_confirmation;
      confirmModal.classList.remove('hidden');
    } else {
      confirmModal.classList.add('hidden');
    }

    // 7. Recent Actions Feed
    if (data.recent_actions && data.recent_actions.length > 0) {
      actionFeed.innerHTML = data.recent_actions.map(act => `
        <div class="action-entry ${act.verified ? 'verified' : 'failed'}">
          <span class="action-name">${act.action} (${act.status})</span>
          <span class="action-meta">
            <span class="${act.verified ? 'badge-verified' : 'badge-failed'}">
              ${act.verified ? 'VERIFIED: OK' : 'VERIFIED: FAILED'}
            </span>
            <span class="action-time" style="color: #7ba3c2; margin-left: 0.5rem;">${act.timestamp}</span>
          </span>
        </div>
      `).join('');
    }
  }

  // Start polling
  pollStatus();
});

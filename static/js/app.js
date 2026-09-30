document.addEventListener('DOMContentLoaded', () => {
  setupTabNavigation();
  setupFormLoaders();
  setupTipFetcher();
});

function setupTabNavigation() {
  const tabs = document.querySelectorAll('.day-tab-btn');
  const cards = document.querySelectorAll('.day-plan-card');

  if (!tabs.length || !cards.length) return;

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const selectedDay = tab.dataset.day;

      tabs.forEach(t => t.classList.toggle('active', t === tab));
      cards.forEach(card => {
        const matches = card.dataset.day === selectedDay || selectedDay === 'all';
        card.style.display = matches ? 'block' : 'none';
      });
    });
  });
}

function setupFormLoaders() {
  const activeForms = document.querySelectorAll('form[data-loading]');

  activeForms.forEach(form => {
    form.addEventListener('submit', () => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (!submitBtn) return;

      submitBtn.disabled = true;
      const label = form.dataset.loadingText || 'Processing request...';
      submitBtn.innerHTML = `<span class="spinner"></span> ${label}`;
    });
  });
}

function setupTipFetcher() {
  const triggerBtn = document.getElementById('fetch-quick-tip-btn');
  const outputBox = document.getElementById('quick-tip-result');

  if (!triggerBtn || !outputBox) return;

  triggerBtn.addEventListener('click', async () => {
    const goalInput = document.getElementById('tip-goal-select');
    const selectedGoal = goalInput?.value || 'Overall Health';

    triggerBtn.disabled = true;
    triggerBtn.innerHTML = `<span class="spinner"></span> Loading Insight...`;
    outputBox.innerHTML = `<div class="alert alert-info">Retrieving fitness recommendation...</div>`;

    try {
      const res = await fetch('/api/nutrition/tip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: selectedGoal })
      });

      const payload = await res.json();
      if (res.ok) {
        outputBox.innerHTML = `
          <div class="alert alert-success">
            <strong>✨ Advice for ${payload.goal}:</strong>
            <p class="mt-1">${payload.tip}</p>
          </div>
        `;
      } else {
        outputBox.innerHTML = `
          <div class="alert alert-danger">
            ${payload.detail || 'Unable to retrieve advice right now.'}
          </div>
        `;
      }
    } catch {
      outputBox.innerHTML = `
        <div class="alert alert-danger">
          Connection lost. Please check your network and retry.
        </div>
      `;
    } finally {
      triggerBtn.disabled = false;
      triggerBtn.innerHTML = `Fetch Advice`;
    }
  });
}
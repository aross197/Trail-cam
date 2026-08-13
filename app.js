document.addEventListener('DOMContentLoaded', () => {

  // TAB SWITCHING
  const navButtons = document.querySelectorAll('.nav-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  navButtons.forEach(button => {
    button.addEventListener('click', () => {
      const targetTab = button.getAttribute('data-tab');
      
      navButtons.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      button.classList.add('active');
      document.getElementById(`tab-${targetTab}`).classList.add('active');
    });
  });

  // MODAL CONTROLS
  const loginModal = document.getElementById('login-modal');
  const btnLoginOpen = document.getElementById('btn-login-open');
  const btnLoginClose = document.getElementById('btn-login-close');
  const loginForm = document.getElementById('login-form');

  if (btnLoginOpen) btnLoginOpen.addEventListener('click', () => loginModal.classList.add('active'));
  if (btnLoginClose) btnLoginClose.addEventListener('click', () => loginModal.classList.remove('active'));

  // FORM SUBMISSION (No local mock data)
  if (loginForm) {
    loginForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const actId = document.getElementById('act-id').value;
      
      // Placeholder state update until backend API handler is attached
      alert(`Connecting ${actId} to backend API service...`);
      loginModal.classList.remove('active');
    });
  }

  // CHAT INPUT HANDLERS
  setupChatForm('global-chat-form', 'global-chat-input', 'global-chat-log');
  setupChatForm('spectate-chat-form', 'spectate-chat-input', 'spectate-chat-log');

  function setupChatForm(formId, inputId, logId) {
    const form = document.getElementById(formId);
    const input = document.getElementById(inputId);
    const log = document.getElementById(logId);

    if (!form) return;

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      const msgDiv = document.createElement('div');
      msgDiv.className = 'chat-msg';
      msgDiv.innerHTML = `<strong>You:</strong> ${text}`;
      log.appendChild(msgDiv);
      
      input.value = '';
      log.scrollTop = log.scrollHeight;
    });
  }

});

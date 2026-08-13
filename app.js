document.addEventListener('DOMContentLoaded', () => {

  // MOCK MATCH DATA
  const mockMatches = [
    { mode: 'Hardpoint', map: 'Standoff', result: 'WIN', kda: '28 / 6 / 9', score: '6,420' },
    { mode: 'Search & Destroy', map: 'Firing Range', result: 'WIN', kda: '12 / 3 / 2', score: '3,810' },
    { mode: 'Domination', map: 'Raid', result: 'LOSS', kda: '19 / 14 / 8', score: '4,150' },
    { mode: 'Team Deathmatch', map: 'Summit', result: 'WIN', kda: '22 / 5 / 4', score: '5,100' }
  ];

  // MOCK FRIENDS LIST
  const mockFriends = [
    { name: 'Soap_NUK3', status: 'online', mode: 'In Ranked Lobby' },
    { name: 'Gaz_NUK3', status: 'online', mode: 'In Match (Standoff)' },
    { name: 'Roach_NUK3', status: 'offline', mode: 'Last seen 2h ago' }
  ];

  // TAB SWITCHING LOGIC
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

  // POPULATE MATCH HISTORY
  const matchTableBody = document.getElementById('match-history-rows');
  mockMatches.forEach(m => {
    const row = document.createElement('tr');
    const resultClass = m.result === 'WIN' ? 'result-win' : 'result-loss';
    row.innerHTML = `
      <td>${m.mode}</td>
      <td>${m.map}</td>
      <td class="${resultClass}">${m.result}</td>
      <td>${m.kda}</td>
      <td>${m.score}</td>
    `;
    matchTableBody.appendChild(row);
  });

  // POPULATE FRIENDS LIST
  const friendsUl = document.getElementById('friends-list-ul');
  mockFriends.forEach(f => {
    const li = document.createElement('li');
    li.className = 'friend-item';
    li.innerHTML = `
      <span class="status-indicator status-${f.status}"></span>
      <div>
        <strong>${f.name}</strong>
        <p style="font-size:0.75rem; color: var(--text-muted);">${f.mode}</p>
      </div>
    `;
    friendsUl.appendChild(li);
  });

  // LOGIN MODAL CONTROLS
  const loginModal = document.getElementById('login-modal');
  const btnLoginOpen = document.getElementById('btn-login-open');
  const btnLoginClose = document.getElementById('btn-login-close');
  const loginForm = document.getElementById('login-form');
  const userNavArea = document.getElementById('user-nav-area');
  const userActivisionId = document.getElementById('user-activision-id');

  btnLoginOpen.addEventListener('click', () => loginModal.classList.add('active'));
  btnLoginClose.addEventListener('click', () => loginModal.classList.remove('active'));

  loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const actId = document.getElementById('act-id').value;
    
    // Update UI state to logged in
    userActivisionId.textContent = actId;
    userNavArea.innerHTML = `<span style="color:var(--accent-green); font-weight:600;"><i class="fa-solid fa-circle-check"></i> ${actId}</span>`;
    
    loginModal.classList.remove('active');
  });

  // CHAT LOGIC SIMULATION
  setupChatForm('global-chat-form', 'global-chat-input', 'global-chat-log');
  setupChatForm('spectate-chat-form', 'spectate-chat-input', 'spectate-chat-log');

  function setupChatForm(formId, inputId, logId) {
    const form = document.getElementById(formId);
    const input = document.getElementById(inputId);
    const log = document.getElementById(logId);

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

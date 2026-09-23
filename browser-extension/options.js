const DEFAULT_HOST = 'http://localhost:8080';

const hostInput = document.getElementById('host');
const saveButton = document.getElementById('save');
const statusDiv = document.getElementById('status');

chrome.storage.sync.get({ wishdeckHost: DEFAULT_HOST }, (result) => {
  hostInput.value = result.wishdeckHost || DEFAULT_HOST;
});

saveButton.addEventListener('click', () => {
  const value = hostInput.value.trim() || DEFAULT_HOST;
  chrome.storage.sync.set({ wishdeckHost: value }, () => {
    statusDiv.textContent = 'Saved.';
    setTimeout(() => { statusDiv.textContent = ''; }, 2000);
  });
});

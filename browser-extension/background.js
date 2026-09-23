const DEFAULT_HOST = 'http://localhost:8080';

function getWishdeckHost() {
  return new Promise((resolve) => {
    if (typeof chrome !== 'undefined' && chrome.storage) {
      chrome.storage.sync.get({ wishdeckHost: DEFAULT_HOST }, (result) => {
        resolve(result.wishdeckHost || DEFAULT_HOST);
      });
    } else {
      resolve(DEFAULT_HOST);
    }
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'wishdeck-add',
    title: 'Add to WishDeck',
    contexts: ['page', 'link', 'selection'],
  });
});

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const url = info.linkUrl || info.pageUrl || (tab && tab.url);
  const title = tab && tab.title ? tab.title : '';
  if (!url) return;

  const host = await getWishdeckHost();
  const target = new URL('/add', host);
  target.searchParams.set('url', url);
  target.searchParams.set('title', title);
  target.searchParams.set('source', 'extension');

  chrome.tabs.create({ url: target.toString() });
});

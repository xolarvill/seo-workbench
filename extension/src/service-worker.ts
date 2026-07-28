chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: false }).catch(() => undefined);

chrome.action.onClicked.addListener(async (tab) => {
  if (tab.id === undefined || tab.windowId === undefined) return;
  await chrome.sidePanel.open({ windowId: tab.windowId });
  await chrome.runtime.sendMessage({ type: "scan-active-tab", tabId: tab.id, url: tab.url }).catch(() => undefined);
});

export {};

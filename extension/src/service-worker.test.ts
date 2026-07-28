import { expect, it, vi } from "vitest";


it("opens the panel from an action gesture and requests a scan", async () => {
  let onClicked: ((tab: chrome.tabs.Tab) => void | Promise<void>) | undefined;
  const setPanelBehavior = vi.fn().mockResolvedValue(undefined);
  const open = vi.fn().mockResolvedValue(undefined);
  const sendMessage = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("chrome", {
    action: { onClicked: { addListener: (listener: typeof onClicked) => { onClicked = listener; } } },
    sidePanel: { open, setPanelBehavior },
    runtime: { sendMessage },
  });

  await import("./service-worker");
  expect(setPanelBehavior).toHaveBeenCalledWith({ openPanelOnActionClick: false });
  expect(onClicked).toBeTypeOf("function");
  await onClicked?.({ id: 42, windowId: 7, url: "https://example.com/" });

  expect(open).toHaveBeenCalledWith({ windowId: 7 });
  expect(sendMessage).toHaveBeenCalledWith({ type: "scan-active-tab", tabId: 42, url: "https://example.com/" });
});

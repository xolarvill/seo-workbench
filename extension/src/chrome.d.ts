declare namespace chrome {
  namespace runtime {
    const id: string;
    function getManifest(): { version: string };
  }

  namespace sidePanel {
    function setPanelBehavior(options: { openPanelOnActionClick: boolean }): Promise<void>;
  }

  namespace tabs {
    interface Tab {
      id?: number;
      url?: string;
      title?: string;
    }
    function query(queryInfo: { active: boolean; currentWindow: boolean }): Promise<Tab[]>;
    function create(createProperties: { url: string }): Promise<Tab>;
    const onActivated: {
      addListener(callback: (activeInfo: { tabId: number; windowId: number }) => void): void;
      removeListener(callback: (activeInfo: { tabId: number; windowId: number }) => void): void;
    };
    const onUpdated: {
      addListener(callback: (tabId: number, changeInfo: { url?: string }, tab: Tab) => void): void;
      removeListener(callback: (tabId: number, changeInfo: { url?: string }, tab: Tab) => void): void;
    };
  }

  namespace scripting {
    interface InjectionResult<T> { result?: T }
    function executeScript<T>(injection: {
      target: { tabId: number };
      func: () => T;
    }): Promise<Array<InjectionResult<T>>>;
  }

  namespace storage.local {
    function get(keys?: string | string[]): Promise<Record<string, unknown>>;
    function set(items: Record<string, unknown>): Promise<void>;
    function remove(keys: string | string[]): Promise<void>;
  }
}

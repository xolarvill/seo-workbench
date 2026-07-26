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

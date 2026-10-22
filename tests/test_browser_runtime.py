import json
from pathlib import Path
from types import SimpleNamespace

import pytest
pytest.importorskip("playwright")
from seo_workbench_tools import browser_runtime as runtime


class Browser:
    version = 'matching-test-browser'
    def __init__(self):
        self.connected = True
        self.closed_contexts = []
        self.contexts = [SimpleNamespace(close=lambda: self.closed_contexts.append(True))]
    def on(self, _event, callback): self.disconnected = callback
    def new_browser_cdp_session(self): raise RuntimeError('not available')
    def is_connected(self): return self.connected
    def close(self): self.connected = False; self.disconnected()


def test_bundled_headless_shell_is_used_without_system_chrome(tmp_path, monkeypatch):
    import playwright
    package = Path(playwright.__file__).parent / 'driver/package'
    specs = json.loads((package/'browsers.json').read_text())['browsers']
    revision = next(s['revision'] for s in specs if s['name']=='chromium-headless-shell')
    shell = tmp_path/f'chromium_headless_shell-{revision}'/'platform'/'chrome-headless-shell'
    shell.parent.mkdir(parents=True); shell.write_text('fixture'); shell.chmod(0o700)
    monkeypatch.delenv('CHROME_PATH', raising=False)
    monkeypatch.setenv('PLAYWRIGHT_BROWSERS_PATH',str(tmp_path))
    assert runtime.browser_executable() == str(shell)


def test_explicit_browser_path_is_validated(tmp_path, monkeypatch):
    monkeypatch.setenv('CHROME_PATH',str(tmp_path/'missing'))
    with pytest.raises(RuntimeError, match='CHROME_PATH'): runtime.browser_executable()


def test_browser_jobs_cannot_overlap(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    with runtime.browser_lease():
        with pytest.raises(RuntimeError,match='already running'):
            with runtime.browser_lease(): pytest.fail('second job must not start')


def test_collection_exception_closes_contexts_and_browser_and_preserves_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setattr(runtime,'browser_executable',lambda *_:'/fixture/browser')
    browser = Browser()
    driver = SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_:browser))
    path = tmp_path/'diagnostic.json'
    with pytest.raises(ValueError):
        with runtime.managed_browser(driver,path): raise ValueError('secret-token=http://private')
    assert not browser.connected
    assert browser.closed_contexts == [True]
    data=json.loads(path.read_text())
    assert data['stage']=='collection' and data['status']=='failed'
    assert 'secret-token' not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600


def test_launch_failure_preserves_signal_and_does_not_retry(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setattr(runtime,'browser_executable',lambda *_:'/fixture/browser')
    attempts=[]
    def launch(**_):
        attempts.append(True)
        raise RuntimeError('<launched> pid=123\nEPERM signal=SIGABRT exitCode=9 secret-private-url')
    path=tmp_path/'diagnostic.json'
    with pytest.raises(RuntimeError):
        with runtime.managed_browser(SimpleNamespace(chromium=SimpleNamespace(launch=launch)),path): pass
    data=json.loads(path.read_text())
    assert len(attempts)==1
    assert data['browser_pid']==123 and data['exit_signal']=='SIGABRT'
    assert data['classification']=='permission_denied'
    assert 'secret-private' not in path.read_text()


def test_expected_browser_shutdown_is_not_reported_as_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setattr(runtime,'browser_executable',lambda *_:'/fixture/browser')
    browser=Browser(); path=tmp_path/'ok.json'
    with runtime.managed_browser(SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_:browser)),path): pass
    assert json.loads(path.read_text())['status']=='ok'


def test_full_chromium_only_resolution_reuses_active_driver(tmp_path, monkeypatch):
    monkeypatch.delenv('CHROME_PATH', raising=False)
    monkeypatch.setenv('PLAYWRIGHT_BROWSERS_PATH',str(tmp_path))
    executable=tmp_path/'full-browser'; executable.write_text('fixture'); executable.chmod(0o700)
    driver=SimpleNamespace(chromium=SimpleNamespace(executable_path=str(executable)))
    assert runtime.browser_executable(driver)==str(executable)


def test_diagnostic_write_failure_still_cleans_up_started_browser(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setattr(runtime,'browser_executable',lambda *_:'/fixture/browser')
    browser=Browser()
    diagnostic=tmp_path/'existing-directory';diagnostic.mkdir()
    with pytest.raises(OSError):
        with runtime.managed_browser(SimpleNamespace(chromium=SimpleNamespace(launch=lambda **_:browser)),diagnostic):pass
    assert not browser.connected and browser.closed_contexts


def test_browser_control_rejects_symlink_ancestor(tmp_path, monkeypatch):
    root=tmp_path/'project';root.mkdir()
    outside=tmp_path/'outside';outside.mkdir()
    (root/'.runtime').symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(runtime,'ROOT',root)
    with pytest.raises(ValueError,match='symlink'):
        with runtime.browser_lease():pytest.fail('symlink must be rejected')
    assert not list(outside.iterdir())


def test_capture_prepares_project_path_before_full_browser_driver_starts(tmp_path, monkeypatch):
    import os
    import playwright.sync_api
    from seo_workbench_tools import rendered_probe
    monkeypatch.setattr(runtime,'ROOT',tmp_path)
    monkeypatch.setattr(runtime,'LOCAL_BROWSERS',tmp_path/'browsers')
    monkeypatch.delenv('CHROME_PATH',raising=False)
    monkeypatch.delenv('PLAYWRIGHT_BROWSERS_PATH',raising=False)
    executable=tmp_path/'browsers/full-browser';executable.parent.mkdir();executable.write_text('fixture');executable.chmod(0o700)
    browser=Browser()
    def new_context(**_):
        def fail():raise RuntimeError('fixture page unavailable')
        return SimpleNamespace(new_page=fail,close=lambda:None)
    browser.new_context=new_context
    def launch(**kwargs):
        assert kwargs['executable_path']==str(executable)
        return browser
    class Driver:
        def __enter__(self):
            assert os.environ['PLAYWRIGHT_BROWSERS_PATH']==str(executable.parent)
            return SimpleNamespace(chromium=SimpleNamespace(executable_path=str(executable),launch=launch))
        def __exit__(self,*_):pass
    monkeypatch.setattr(playwright.sync_api,'sync_playwright',lambda:Driver())
    report=rendered_probe.capture(['https://example.com/'],tmp_path/'output',1,0)
    assert report['browser_runtime']['executable']==str(executable)
    assert report['collection_status']=='failed'
    assert not browser.connected

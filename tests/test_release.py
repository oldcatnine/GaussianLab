"""Release entrypoint and publication safety checks without network mutations."""
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_release_entry_defers_gui_until_run():
    spec = importlib.util.spec_from_file_location("release_entry", ROOT / "app_entry.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(module.main)


def test_distribution_includes_guide_and_source_notice():
    for file in ("USER_GUIDE-v0.1.0.md", "release-notes-v0.1.0.md", "THIRD-PARTY-NOTICES.md"):
        assert (ROOT / "docs" / file).is_file()
    text = (ROOT / "docs/THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
    assert "LGPL" in text and "Corresponding-Source.zip" in text
    assert "_internal" in text
    spec = (ROOT / "GaussianLab.spec").read_text(encoding="utf-8")
    assert "'qpdf.dll'" in spec and "'qtvirtualkeyboardplugin.dll'" in spec
    assert "runtime_names" in spec and "pyside_path / name" in spec
    assert "'icuuc.dll'" in spec


def test_publisher_requires_explicit_action_and_has_no_hardcoded_token():
    command = subprocess.run([sys.executable, str(ROOT / "scripts/publish_github.py"), "--help"],
                             capture_output=True, text=True)
    assert command.returncode == 0
    assert "--visibility" in command.stdout
    text = (ROOT / "scripts/publish_github.py").read_text(encoding="utf-8")
    assert "GIT_TERMINAL_PROMPT" in text
    assert "'ghp_" not in text and '"ghp_' not in text


def test_upload_reader_and_bulk_proxy_configuration(tmp_path):
    spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish_github.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / 'sample.bin'
    path.write_bytes(b'abc' * 100)
    stream = module.UploadReader(path)
    try:
        assert len(stream) == 300
        assert stream.read(7) == b'abcabca'
        assert stream.tell() == 7
    finally:
        stream.close()
    adapter = module.BulkUploadAdapter()
    assert adapter.poolmanager.connection_pool_kw['blocksize'] == 1024**2
    proxy = adapter.proxy_manager_for('http://localhost:12345')
    assert proxy.connection_pool_kw['blocksize'] == 1024**2

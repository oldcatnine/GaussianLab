"""Verify final release hashes/ZIP CRCs and extract a standalone test copy."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    release = ROOT / 'releases/v0.1.0'
    checked = []
    for line in (release / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected, name = line.split('  ', 1)
        path = release / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == expected, name
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None, name
            if 'Windows-x64' in name:
                names = archive.namelist()
                assert any(n.endswith('/GaussianLab.exe') for n in names)
                assert any(n.endswith('THIRD_PARTY_LICENSES/CPython/LICENSE.txt') for n in names)
                assert any(n.endswith('/LGPL-3.0-only.txt') for n in names)
                forbidden = ('icuuc.dll', 'qtvirtualkeyboardplugin.dll', 'qpdf.dll', 'Qt6DataVisualization.dll')
                assert not any(n.rsplit('/', 1)[-1] in forbidden for n in names)
                destination = ROOT / 'outputs/portable-check'
                if destination.exists():
                    raise RuntimeError('Standalone test folder already exists; choose a fresh test location')
                destination.mkdir(parents=True)
                archive.extractall(destination)
        checked.append({'name': name, 'bytes': path.stat().st_size, 'sha256': actual, 'zip_crc': 'passed'})
    (ROOT / 'docs/release-artifacts-v0.1.0.json').write_text(json.dumps(checked, indent=2), encoding='utf-8')
    print(json.dumps(checked, indent=2))


if __name__ == '__main__':
    main()

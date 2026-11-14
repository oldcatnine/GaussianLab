"""认证下载已发布附件，校验摘要并解压独立测试副本。"""
import argparse
import sys
import time
import hashlib
import json
from pathlib import Path
import zipfile
from publish_github import session, api

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gaussian_lab import __version__


def download(client, asset, target):
    with client.get(asset['url'], headers={'Accept':'application/octet-stream'}, stream=True, timeout=(15,90)) as response:
        response.raise_for_status()
        if 'json' in response.headers.get('Content-Type','').lower():
            raise RuntimeError('应收到二进制附件，实际返回了 JSON 数据')
        downloaded, last = 0, 0
        with target.open('wb') as output:
            for chunk in response.iter_content(1024**2):
                output.write(chunk)
                downloaded += len(chunk)
                if downloaded-last >= 32*1024**2:
                    print(json.dumps({'downloading':asset['name'],'bytes':downloaded}),flush=True)
                    last = downloaded
    assert target.stat().st_size == asset['size']


def main():
    parser = argparse.ArgumentParser(description="下载并核验明确指定的已发布版本，不创建或覆盖远端发行")
    parser.add_argument("--tag", default="v" + __version__)
    args = parser.parse_args()
    client = session()
    repo = api(client, 'GET', '/repos/oldcatnine/GaussianLab')
    release = api(client, 'GET', '/repos/oldcatnine/GaussianLab/releases/tags/' + args.tag)
    assert repo['private'] and not release['draft']
    assets = {a['name']:a for a in release['assets']}
    expected_assets = {f'GaussianLab-{args.tag}-Windows-x64.zip',
                       f'GaussianLab-{args.tag}-Qt-Corresponding-Source.zip', 'SHA256SUMS.txt'}
    if args.tag != 'v0.1.0':
        expected_assets.add(f'GaussianLab-{args.tag}-Application-Source.zip')
    assert set(assets) == expected_assets
    folder = ROOT / 'outputs' / f'github-download-{args.tag}-{time.time_ns()}'
    folder.mkdir(parents=True,exist_ok=True)
    download(client, assets['SHA256SUMS.txt'], folder/'SHA256SUMS.txt')
    checked = []
    for line in (folder/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        expected,name=line.split('  ',1)
        asset=assets[name]
        target=folder/name
        download(client,asset,target)
        actual=hashlib.sha256(target.read_bytes()).hexdigest()
        assert actual == expected, name
        digest=asset.get('digest')
        if digest:
            assert digest == 'sha256:'+actual, name
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
            if 'Windows-x64' in name:
                destination=folder/'remote-portable-check'
                if destination.exists():
                    raise RuntimeError('远端发行包的独立测试目录已经存在')
                destination.mkdir(parents=True)
                archive.extractall(destination)
        checked.append({'name':name,'bytes':asset['size'],'sha256':actual,
                        'github_digest':digest,'url':asset['browser_download_url']})
    report={'repository':repo['html_url'],'private':repo['private'],'tag':release['tag_name'],
            'release':release['html_url'],'draft':release['draft'],'assets':checked,
            'verification':'已下载，SHA-256 与发布清单一致，压缩包完整性检查通过'}
    (ROOT/f'docs/github-release-{args.tag}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()

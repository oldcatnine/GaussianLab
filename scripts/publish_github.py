"""通过 Git 凭据管理器和官方接口发布版本，不输出秘密信息。

必须显式指定操作；状态查询只读，创建和发布操作使用对应的子命令。
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import requests
from requests.adapters import HTTPAdapter


class BulkUploadAdapter(HTTPAdapter):
    """增大传输块，减少高延迟 HTTP 代理中的小块读写。"""
    def init_poolmanager(self, connections, maxsize, block=False, **kwargs):
        kwargs['blocksize'] = 1024 * 1024
        return super().init_poolmanager(connections, maxsize, block, **kwargs)

    def proxy_manager_for(self, proxy, **kwargs):
        kwargs['blocksize'] = 1024 * 1024
        return super().proxy_manager_for(proxy, **kwargs)


class UploadReader:
    def __init__(self, path):
        self.stream = path.open('rb')
        self.name = str(path)
        self.total = path.stat().st_size
        self.last_report = 0

    def __len__(self):
        return self.total

    def read(self, size=-1):
        data = self.stream.read(size)
        current = self.stream.tell()
        if current - self.last_report >= 16 * 1024**2 or current == self.total:
            print(json.dumps({'sending': Path(self.name).name, 'read_bytes': current, 'total_bytes': self.total}), flush=True)
            self.last_report = current
        return data

    def tell(self):
        return self.stream.tell()

    def close(self):
        self.stream.close()


def session():
    env = dict(os.environ, GCM_INTERACTIVE="never", GIT_TERMINAL_PROMPT="0")
    proc = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                          text=True, capture_output=True, timeout=30, env=env)
    values = dict(line.split("=", 1) for line in proc.stdout.splitlines() if "=" in line)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or values.get("password")
    if not token:
        raise RuntimeError("没有可用于非交互操作的 GitHub 凭据")
    client = requests.Session()
    client.mount('https://uploads.github.com/', BulkUploadAdapter())
    client.headers.update({"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                           "X-GitHub-Api-Version": "2022-11-28"})
    return client


def api(client, method, path, **kwargs):
    response = client.request(method, "https://api.github.com"+path, timeout=60, **kwargs)
    if response.status_code >= 400:
        # 不打印请求头、凭据或未经筛选的响应正文。
        raise RuntimeError(f"GitHub API {method} {path}: HTTP {response.status_code}")
    return response.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["status", "create-repo", "release", "verify"])
    parser.add_argument("--repo", default="GaussianLab")
    parser.add_argument("--visibility", choices=["public", "private"])
    parser.add_argument("--notes", type=Path)
    parser.add_argument("--asset", type=Path, action="append", default=[])
    parser.add_argument("--tag", default="v0.1.0")
    args = parser.parse_args()
    client = session()
    user = api(client, "GET", "/user")["login"]
    repo_path = f"/repos/{user}/{args.repo}"
    if args.action == "status":
        print(json.dumps({"authenticated": True, "login": user}))
    elif args.action == "create-repo":
        if args.visibility is None:
            parser.error("创建仓库必须指定 --visibility")
        response = client.get("https://api.github.com"+repo_path, timeout=30)
        if response.status_code == 200:
            raise RuntimeError("仓库已经存在，请核对后再操作，程序不会直接覆盖或复用")
        if response.status_code != 404:
            raise RuntimeError(f"仓库检查的 HTTP 状态：{response.status_code}")
        repo = api(client, "POST", "/user/repos", json={"name": args.repo,
            "description": "基于 Python 的高斯光束传播、衍射与交互式三维光学实验台",
            "private": args.visibility == "private", "auto_init": False})
        print(json.dumps({"url": repo["html_url"], "private": repo["private"]}))
    elif args.action == "release":
        if not args.notes or not args.asset:
            parser.error("必须指定 --notes 和 --asset")
        existing = [r for r in api(client, 'GET', repo_path+'/releases') if r['tag_name'] == args.tag]
        if existing:
            data = existing[0]
            if not data['draft']:
                raise RuntimeError('版本已经发布，程序拒绝覆盖')
        else:
            data = api(client, "POST", repo_path+"/releases", json={"tag_name": args.tag,
                "name": "GaussianLab V0.1.0 — Windows 首版", "body": args.notes.read_text(encoding="utf-8"),
                "draft": True, "prerelease": False})
        for path in args.asset:
            present = [a for a in api(client, 'GET', repo_path+f"/releases/{data['id']}/assets") if a['name'] == path.name]
            if present:
                if present[0]['state'] == 'uploaded' and present[0]['size'] == path.stat().st_size:
                    print(json.dumps({'already_uploaded': path.name}), flush=True)
                    continue
                raise RuntimeError('已有附件尚未完成或大小不符，需要先检查')
            stream = UploadReader(path)
            try:
                response = client.post(data["upload_url"].split("{")[0], params={"name": path.name},
                    headers={"Content-Type": "application/octet-stream"}, data=stream, timeout=900)
            finally:
                stream.close()
            if response.status_code != 201:
                raise RuntimeError(f"附件上传：{path.name}: HTTP {response.status_code}；版本仍保持草稿状态")
            print(json.dumps({"uploaded": path.name, "bytes": path.stat().st_size}))
        published = api(client, "PATCH", repo_path+f"/releases/{data['id']}", json={"draft": False})
        print(json.dumps({"release_url": published["html_url"]}))
    else:
        data = api(client, "GET", repo_path+"/releases/tags/"+args.tag)
        print(json.dumps({"url": data["html_url"], "draft": data["draft"], "assets": [
            {"name": a["name"], "size": a["size"], "url": a["browser_download_url"]} for a in data["assets"]]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"发布操作失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)

"""核对文件用途清单，更新学习手册附录并生成可离线阅读、打印的单文件网页。"""
import base64
import html
import json
from pathlib import Path
import re
import subprocess
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
MANUAL = DOCS / '项目学习手册.md'
EXTRA_FILES = ['docs/项目学习手册.md', 'docs/项目学习手册.html', 'docs/file-roles.json',
               'docs/file-inventory.json', 'scripts/build_handbook.py', 'tests/test_text_policy.py',
               'docs/USER_GUIDE-v4.0.5.md', 'docs/release-notes-v4.0.5.md']


def inventory():
    """每个受版本管理的文件都必须有明确用途，新文件没有说明时直接报错。"""
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    names = sorted(set(filter(None, names)) | set(EXTRA_FILES))
    roles = json.loads((DOCS / 'file-roles.json').read_text(encoding='utf-8-sig'))
    rows = []
    for name in names:
        if name in roles:
            purpose = roles[name]
        elif name.startswith('docs/assets/'):
            stem = Path(name).stem
            case = {'focus':'单透镜聚焦', 'expander':'双透镜扩束', 'diffraction':'光阑衍射'}[stem.split('-')[0]]
            purpose = case + ('预置项目输入参数，采用国际单位制。' if name.endswith('.json') else
                              '历史三维场景截图，用于追溯渲染结果。' if '-scene' in name else
                              '历史应用界面截图，用于追溯界面与数值展示。')
        elif name.startswith('.idea/'):
            purpose = {'inspectionProfiles/Project_Default.xml':'本机代码检查配置，包含检查工具与忽略包规则。',
                       'inspectionProfiles/profiles_settings.xml':'本机代码检查方案的启用设置。',
                       'modules.xml':'本机项目模块列表及模块文件引用。',
                       'vcs.xml':'本机集成开发环境的 Git 目录映射。',
                       '.gitignore':'本机集成开发环境生成文件的忽略规则。'}.get(name[6:],
                       '本机 Python 模块与解释器配置，不参与业务计算和发行运行。')
        else:
            raise ValueError('缺少文件用途说明：' + name)
        rows.append({'path':name, 'purpose':purpose, 'optional_local':name.startswith('.idea/')})
    (DOCS / 'file-inventory.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return rows


def build():
    rows = inventory()
    text = MANUAL.read_text(encoding='utf-8')
    table = '| 文件 | 作用 |\n| --- | --- |\n' + '\n'.join(
        f"| `{row['path']}` | {row['purpose']} |" for row in rows)
    text = re.sub(r'<!-- FILE_INDEX_START -->.*?<!-- FILE_INDEX_END -->',
                  '<!-- FILE_INDEX_START -->\n'+table+'\n<!-- FILE_INDEX_END -->', text, flags=re.S)
    MANUAL.write_text(text, encoding='utf-8')
    md = MarkdownIt('commonmark', {'html':True}).enable('table')
    tokens = md.parse(text)
    toc = []
    for i, token in enumerate(tokens):
        if token.type == 'heading_open' and token.tag in ('h2','h3'):
            anchor = 'section-' + str(len(toc)+1)
            token.attrSet('id', anchor)
            toc.append((anchor, tokens[i+1].content, token.tag))
    body = md.renderer.render(tokens, md.options, {})
    # 将本地插图嵌入网页，使复制阅读版时不依赖图片目录。
    def embed(match):
        name = match.group(1)
        if name.startswith(('https:', 'http:', 'data:')):
            return match.group(0)
        path = (DOCS / name).resolve()
        mime = 'image/svg+xml' if path.suffix == '.svg' else 'image/png'
        return 'src="data:'+mime+';base64,'+base64.b64encode(path.read_bytes()).decode()+'"'
    body = re.sub(r'src="([^"]+)"', embed, body)
    links = ''.join(f'<a class="{level}" href="#{anchor}">{html.escape(title)}</a>' for anchor,title,level in toc)
    css = '''
    :root{color-scheme:light;font-family:"Microsoft YaHei",sans-serif;color:#233447;background:#eef2f7}
    body{margin:0;line-height:1.85}nav{position:fixed;inset:0 auto 0 0;width:254px;overflow:auto;padding:25px 18px;background:#12273d;color:white}
    nav strong{display:block;margin-bottom:16px}nav a{display:block;color:#c9d9e8;text-decoration:none;font-size:13px;padding:5px 0}nav a:hover{color:white}
    nav .h3{padding-left:13px;font-size:12px}main{margin:28px 30px 40px 314px;max-width:1040px;background:white;padding:38px 45px;border-radius:10px}
    h1{font-size:30px;color:#10283e;line-height:1.4;margin-top:0}h2{font-size:23px;color:#164767;margin-top:44px;scroll-margin-top:20px}h3{font-size:18px;color:#23506d;margin-top:26px}
    p,li{font-size:15px}a{color:#07699b}table{width:100%;border-collapse:collapse;font-size:13px;margin:20px 0;table-layout:auto}th,td{border:1px solid #d7e0e8;padding:9px 11px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf4f9}tr:nth-child(even){background:#fafcfe}
    code{font-family:Consolas,"Microsoft YaHei",monospace;background:#eff4f8;padding:2px 4px;border-radius:3px;font-size:.9em;overflow-wrap:anywhere}pre{padding:16px;background:#f1f5f9;white-space:pre-wrap;overflow-wrap:anywhere;border-radius:6px;line-height:1.6}pre code{padding:0}
    blockquote{border-left:4px solid #5084a5;padding:3px 18px;margin:18px 0;background:#f1f7fa}img,svg{max-width:100%;height:auto}.hint{font-size:12px;color:#627a8d}
    @media(max-width:1000px){nav{position:static;width:auto;max-height:280px}main{margin:15px;padding:25px}}
    @page{size:A4;margin:18mm 16mm}@media print{nav{display:none}body{background:white}main{margin:0;padding:0;border-radius:0;max-width:none}h2{break-before:page}h2:first-of-type{break-before:auto}h2,h3{break-after:avoid}p,li{font-size:10.5pt}td,th{font-size:9pt}tr,pre,blockquote,svg{break-inside:avoid}a{color:inherit;text-decoration:none}}
    '''
    page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GaussianLab 项目学习手册</title><style>'+css+'</style></head><body><nav><strong>GaussianLab 项目学习手册</strong>'+links+'</nav><main>'+body+'</main></body></html>'
    (DOCS / '项目学习手册.html').write_text(page, encoding='utf-8')
    print(f'已生成离线手册，覆盖 {len(rows)} 个文件、{len(toc)} 个导航条目。')


if __name__ == '__main__':
    build()

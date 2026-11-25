"""mkn.github.io: writes _site/ from settings/ (the settings gallery) and mkn/mkn's
doc/mkn/man (the manual, from the latest branch: the released mkn).

    python3 tools/build.py [--mkn <mkn/mkn checkout>] [--out _site]

Without --mkn, mkn/mkn's latest branch is cloned into .cache/mkn (refreshed when it exists).
"""

import argparse
import html
import posixpath
import re
import shutil
import subprocess
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
MKN_REPO = "https://github.com/mkn/mkn"
MKN_BRANCH = "latest"
SITE_REPO = "https://github.com/mkn/mkn.github.io"
RELEASES = f"{MKN_REPO}/releases/latest/download"

# the manual's pages, in the order of its own index (doc/mkn/man/README.md)
DOCS = [
    ("overview", "Overview"),
    ("yaml", "mkn.yaml"),
    ("settings", "settings.yaml"),
    ("cli", "Command line"),
    ("dependencies", "Dependencies"),
    ("behaviour", "Build behaviour"),
    ("env", "Environment variables"),
    ("debugging", "Debugging"),
    ("logging", "Logging"),
    ("build", "Building maiken"),
    ("switches", "Switches"),
]

ASSETS = [
    ("Linux x86_64 (glibc, portable)", "mkn_manylinux"),
    ("Linux arm64 (portable)", "mkn_manylinux_arm"),
    ("Linux x86_64 (Ubuntu)", "mkn_nix"),
    ("Linux arm64 (Ubuntu)", "mkn_arm_linux"),
    ("macOS arm64", "mkn_arm_osx"),
    ("Windows x86_64", "mkn.exe"),
]


def slug(text, separator="-"):
    """a heading's id as GitHub makes it, so the manual's #anchors keep working"""
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", separator)


def esc(text):
    return html.escape(str(text), quote=True)


def page(title, body, active, depth=0):
    """the layout: header, navigation, body, footer"""
    up = "../" * depth
    nav = [("index.html", "Home", "home"), ("settings.html", "Settings", "settings"),
           ("docs/index.html", "Manual", "docs")]
    links = "".join(
        f'<a href="{up}{href}"{" class=\"active\"" if key == active else ""}>{name}</a>'
        for href, name, key in nav
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<header class="top">
  <a class="brand" href="{up}index.html">mkn</a>
  <nav>{links}<a href="{MKN_REPO}">GitHub</a></nav>
</header>
<main>
{body}
</main>
<footer>
  <span>maiken, a build tool for C, C++, CUDA and more. BSD licensed.</span>
  <a href="{SITE_REPO}">Site source</a>
</footer>
</body>
</html>
"""


def code(text, lang=""):
    cls = f' class="language-{lang}"' if lang else ""
    return f"<pre><code{cls}>{esc(text)}</code></pre>"


def index_page():
    rows = "".join(
        f'<tr><td>{esc(name)}</td><td><a href="{RELEASES}/{asset}"><code>{asset}</code></a></td></tr>'
        for name, asset in ASSETS
    )
    body = f"""
<section class="hero">
  <h1>maiken <span class="muted">(mkn)</span></h1>
  <p class="lead">A YAML-driven, cross-platform build tool for C, C++, Obj-C, CUDA, OpenCL and C#.</p>
  <p>One <code>mkn.yaml</code> per project. Dependencies are fetched from git and built for you,
  profiles cover debug, test and platform variants, and the same file works with gcc, clang,
  MSVC, nvcc and hipcc on Linux, macOS, BSD and Windows.</p>
  <div class="pair">
    {code("name: hello" + chr(10) + "main: hello.cpp", "yaml")}
    {code("mkn build run", "sh")}
  </div>
</section>

<section>
  <h2 id="install">Install</h2>
  <p>Prebuilt binaries are published with every
  <a href="{MKN_REPO}/releases/latest">release</a>:</p>
  <table><thead><tr><th>Platform</th><th>Download</th></tr></thead><tbody>{rows}</tbody></table>
  {code("curl -Lo mkn " + RELEASES + "/mkn_manylinux" + chr(10) + "chmod +x mkn && mv mkn ~/.local/bin/   # or anywhere on PATH" + chr(10) + "mkn -v", "sh")}
  <p>A C/C++ compiler and <code>git</code> must be on <code>PATH</code>. On its first run mkn
  detects your compiler and writes a default settings file, which the
  <a href="settings.html">settings examples</a> extend or replace.</p>
</section>

<section>
  <h2 id="commands">Everyday commands</h2>
  <table><tbody>
    <tr><td><code>mkn build</code></td><td>Compile and link, a profile's <code>test:</code> executables too</td></tr>
    <tr><td><code>mkn test</code></td><td>Run the test executables</td></tr>
    <tr><td><code>mkn run</code></td><td>Run the executable, with dependency library paths set up</td></tr>
    <tr><td><code>mkn clean</code></td><td>Delete <code>bin/&lt;profile&gt;</code></td></tr>
  </tbody></table>
  <p>Combine them, with a profile and a settings file: <code>mkn clean build test -p test -x clang</code>.
  Everything else is in the <a href="docs/index.html">manual</a>.</p>
</section>

<section class="cards">
  <a class="card" href="settings.html"><h3>Settings examples</h3>
  <p>Compilers, sanitizers, MPI, CUDA and HIP on Linux, macOS and Windows, each built in CI.</p></a>
  <a class="card" href="docs/index.html"><h3>Manual</h3>
  <p><code>mkn.yaml</code>, <code>settings.yaml</code>, the command line, dependencies and more.</p></a>
</section>
"""
    return page("maiken (mkn)", body, "home")


def leading_comment(text):
    """a settings file's description: its leading # lines, joined into paragraphs"""
    lines = []
    for line in text.splitlines():
        if line.startswith("#"):
            lines.append(line.lstrip("#").strip())
        elif lines or line.strip():
            break
    return " ".join(lines)


def settings_page(out):
    catalog = yaml.safe_load((ROOT / "settings" / "catalog.yaml").read_text())
    toc, sections = [], []
    for os_key, group in catalog.items():
        toc.append(f'<a href="#{os_key}">{esc(group["title"])}</a>')
        cards = []
        for entry in group["entries"]:
            src = ROOT / "settings" / os_key / entry["file"]
            text = src.read_text()
            dest = out / "settings" / os_key / entry["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            anchor = f"{os_key}-{Path(entry['file']).stem}".replace("_", "-")
            tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in entry.get("tags", []))
            ci = entry.get("ci")
            badge = (f'<span class="badge ok" title="the example project is built, tested and run with it">built in CI: {esc(ci)}</span>'
                     if ci else '<span class="badge" title="needs hardware the CI runners lack">not built in CI</span>')
            rel = f"settings/{os_key}/{entry['file']}"
            use = (  # default: the settings file mkn could not write itself, no super: settings
                "Use: save as mkn's default settings file, the path its message prints: "
                "<code>maiken/settings.yaml</code> in <code>%HOME%</code>, else in "
                "<code>%HOMEDRIVE%%HOMEPATH%</code>; then <code>mkn build</code> needs no "
                "<code>-x</code>"
                if entry.get("default") else
                f"Use: <code>mkn build -x {esc(Path(entry['file']).stem)}</code> with the file saved "
                "next to the project or in the settings directory")
            cards.append(f"""
<article class="example" id="{anchor}">
  <header><h3><a href="#{anchor}">{esc(entry["title"])}</a></h3>{tags}{badge}</header>
  <p>{esc(leading_comment(text))}</p>
  {code(text, "yaml")}
  <p class="use">{use}, or <a href="{rel}" download>download</a> /
  <a href="{SITE_REPO}/blob/main/{rel}">view on GitHub</a></p>
</article>""")
        intro = markdown.markdown(group["intro"], extensions=["fenced_code", "tables"]) if group.get("intro") else ""
        sections.append(f'<section><h2 id="{os_key}">{esc(group["title"])}</h2>'
                        f'<div class="prose intro">{intro}</div>{"".join(cards)}</section>')
    body = f"""
<h1>Settings examples</h1>
<p class="lead">A settings file says which compiler, archiver and linker build each file type,
plus include paths, library paths, environment and properties. mkn writes a default one on its
first run; <code>-x &lt;file&gt;</code> selects another, and <code>super: settings</code> extends the
default. See <a href="docs/settings.html">settings.yaml</a> for every key.</p>
<p>Each example below marked <em>built in CI</em> builds, tests and runs
<a href="{SITE_REPO}/tree/main/example">a small project</a> on that runner with the released mkn.</p>
<nav class="toc">{"".join(toc)}</nav>
{"".join(sections)}
"""
    return page("Settings examples - mkn", body, "settings")


def doc_link(match, rel_dir):
    """a manual link: x.md[#a] to x.html[#a] among the pages, others to GitHub"""
    target = match.group(2)
    if re.match(r"^[a-z]+:", target) or target.startswith("#"):
        return match.group(0)
    path, _, anchor = target.partition("#")
    name = posixpath.basename(path)
    if posixpath.dirname(path) == "" and name.endswith(".md"):
        stem = name[:-3]
        page_name = "index" if stem == "README" else stem
        return f"{match.group(1)}({page_name}.html{'#' + anchor if anchor else ''})"
    repo_path = posixpath.normpath(posixpath.join(rel_dir, path))
    return f"{match.group(1)}({MKN_REPO}/blob/{MKN_BRANCH}/{repo_path}{'#' + anchor if anchor else ''})"


def render_md(text, rel_dir):
    text = re.sub(r"(\]\s*)\(([^)\s]+)\)", lambda m: doc_link(m, rel_dir), text)
    md = markdown.Markdown(
        extensions=["fenced_code", "tables", "toc"],
        extension_configs={"toc": {"slugify": slug}},
    )
    return md.convert(text)


def docs_pages(out, mkn_dir):
    man = mkn_dir / "doc" / "mkn" / "man"
    rel_dir = "doc/mkn/man"
    side = "".join(f'<a href="{name}.html">{esc(title)}</a>' for name, title in DOCS)
    pages = [("index", "README", "maiken manual")] + [(n, n, t) for n, t in DOCS]
    for name, source, title in pages:
        body_html = render_md((man / f"{source}.md").read_text(), rel_dir)
        edit = f"{MKN_REPO}/blob/{MKN_BRANCH}/{rel_dir}/{source}.md"
        body = f"""
<div class="docs">
  <aside><a href="index.html"><strong>Manual</strong></a>{side}</aside>
  <article class="prose">{body_html}
  <p class="edit"><a href="{edit}">This page in mkn/mkn</a></p></article>
</div>"""
        (out / "docs" / f"{name}.html").write_text(page(f"{title} - mkn", body, "docs", depth=1))


def mkn_checkout(given):
    if given:
        return Path(given).resolve()
    dest = ROOT / ".cache" / "mkn"
    if dest.exists():
        subprocess.run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", MKN_BRANCH], check=True)
        subprocess.run(["git", "-C", str(dest), "checkout", "-q", "FETCH_HEAD"], check=True)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--depth", "1", "-b", MKN_BRANCH, f"{MKN_REPO}.git", str(dest)], check=True)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mkn", help="an mkn/mkn checkout, default: latest cloned into .cache/mkn")
    parser.add_argument("--out", default=str(ROOT / "_site"))
    args = parser.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "docs").mkdir(parents=True)
    shutil.copyfile(ROOT / "static" / "style.css", out / "style.css")
    (out / ".nojekyll").write_text("")
    (out / "index.html").write_text(index_page())
    (out / "settings.html").write_text(settings_page(out))
    docs_pages(out, mkn_checkout(args.mkn))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

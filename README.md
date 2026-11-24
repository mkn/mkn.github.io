# mkn.github.io

The maiken (`mkn`) website, served by GitHub Pages at https://mkn.github.io/.

| Edit this | to change |
|---|---|
| `settings/<os>/*.yaml` | a settings example; its leading comment is its description on the site |
| `settings/catalog.yaml` | which examples are shown, their titles and tags, and the CI runner each is built on |
| `example/` | the project every example builds, tests and runs in CI |
| `tools/build.py` | the pages: home, settings examples, the manual's layout |
| `static/style.css` | the look |

The manual is not here: it is `doc/mkn/man/` in [mkn/mkn](https://github.com/mkn/mkn/tree/latest/doc/mkn/man),
so a change to mkn and its documentation are one PR there. The site renders its `latest` branch
(the released mkn), rebuilt on every push here and daily.

## Build locally

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python tools/build.py            # mkn/mkn's latest cloned into .cache/mkn, or --mkn <checkout>
.venv/bin/python tools/check.py            # internal links and #anchors
python3 -m http.server -d _site            # http://localhost:8000
```

## Try a settings example

```sh
cd example
mkn clean build test run -p app -x ../settings/linux/clang.yaml
```

## CI

- `pages.yml`: builds and checks the site, deploys it from `main` (Pages source: GitHub Actions)
- `settings.yml`: every example with a `ci:` runner in `settings/catalog.yaml` builds, tests and
  runs `example/` there with the released mkn; weekly as well, as runner images change

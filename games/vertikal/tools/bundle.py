# -*- coding: utf-8 -*-
"""Собирает ES-модули игры в один файл.

Каждый модуль оборачивается в IIFE и возвращает объект экспортов — так
сохраняется изоляция областей видимости. Плоская склейка сломалась бы:
в i18n.js есть приватная `current`, а lotto.js экспортирует свою `current`.
"""
import io, re, os, json

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src') + os.sep
ORDER = ['rng', 'balance', 'suspicion', 'loyalty', 'events', 'clicker', 'state',
         'i18n', 'art', 'audio', 'sdk', 'storage', 'main']

IMPORT_NS = re.compile(r"^import\s+\*\s+as\s+(\w+)\s+from\s+'\./(\w+)\.js';?\s*$", re.M)
IMPORT_NAMED = re.compile(r"^import\s*\{([^}]*)\}\s*from\s+'\./(\w+)\.js';?\s*$", re.M)
IMPORT_DEFAULT = re.compile(r"^import\s+\w+\s+from\s+'[^']+';?\s*$", re.M)
EXPORT_LIST = re.compile(r"^export\s*\{([^}]*)\};?\s*$", re.M)

def named_binding(m):
    """`import { a, b as c } from './mod.js'` -> `var {a, b: c} = __m['mod'];`

    Псевдоним в деструктуризации пишется через двоеточие, а не через `as`.
    Дословная подстановка спецификаторов давала `{suspend as audioSuspend}` —
    невалидный JS, из-за которого опубликованная сборка падала целиком.
    """
    specs = []
    for part in m.group(1).split(','):
        part = part.strip()
        if not part:
            continue
        if ' as ' in part:
            src, dst = part.split(' as ', 1)
            specs.append('%s: %s' % (src.strip(), dst.strip()))
        else:
            specs.append(part)
    return "var {%s} = __m['%s'];" % (', '.join(specs), m.group(2))


def exports_of(code):
    names = []
    for m in re.finditer(r"^export\s+(?:async\s+)?function\s+(\w+)", code, re.M):
        names.append(m.group(1))
    for m in re.finditer(r"^export\s+(?:const|let|var)\s+(\w+)", code, re.M):
        names.append(m.group(1))
    for m in EXPORT_LIST.finditer(code):
        for part in m.group(1).split(','):
            part = part.strip()
            if not part:
                continue
            names.append(part.split(' as ')[-1].strip())
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n); out.append(n)
    return out

# Страховка от забытого модуля: любой './x.js', на который ссылается импорт,
# обязан быть в ORDER, иначе бандл соберётся с undefined вместо модуля.
referenced = set()
for name in ORDER:
    src = io.open(SRC + name + '.js', encoding='utf-8').read()
    referenced |= set(re.findall(r"from\s+'\./(\w+)\.js'", src))
missing = sorted(referenced - set(ORDER))
if missing:
    raise SystemExit('в ORDER не хватает модулей: %s' % ', '.join(missing))

parts = ["(function(){\n'use strict';\nvar __m = {};\n"]
for name in ORDER:
    code = io.open(SRC + name + '.js', encoding='utf-8').read()
    names = exports_of(code)

    code = IMPORT_NS.sub(lambda m: "var %s = __m['%s'];" % (m.group(1), m.group(2)), code)
    code = IMPORT_NAMED.sub(named_binding, code)
    code = IMPORT_DEFAULT.sub('', code)
    code = EXPORT_LIST.sub('', code)
    code = re.sub(r"^export\s+", '', code, flags=re.M)

    ret = ('return {%s};' % ', '.join(names)) if names else 'return {};'
    parts.append("__m['%s'] = (function(){\n%s\n%s\n})();\n" % (name, code, ret))
parts.append("})();")
bundle = ''.join(parts)

# Страховка от невалидного бандла: публиковать сборку, которая падает в браузере,
# нельзя. Один раз мы это уже сделали — проверяли исходники и архив, но не
# однофайловую страницу, ровно ту, что ушла игроку.
def _syntax_check(js):
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as f:
        f.write(js); tmp = f.name
    try:
        p = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
    except OSError:
        print('node не найден, синтаксис бандла не проверен'); return
    finally:
        os.unlink(tmp)
    if p.returncode != 0:
        raise SystemExit('бандл невалиден:\n' + (p.stderr or p.stdout))
    print('синтаксис бандла: ок')

_syntax_check(bundle)

css = io.open(os.path.join(os.path.dirname(SRC.rstrip(os.sep)), 'styles.css'), encoding='utf-8').read()
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'build')
os.makedirs(OUT, exist_ok=True)
page = (
    '<title>Вертикаль</title>\n<style>\n' + css + '\nbody{margin:0;background:var(--felt)}\n</style>\n'
    '<div id="app" class="app"><div class="boot" id="boot"><div class="boot__mark">В</div></div></div>\n'
    '<script>\n' + bundle + '\n</script>\n'
)
io.open(os.path.join(OUT, 'vertikal-single.html'), 'w', encoding='utf-8').write(page)
print('модулей: %d | бандл: %d символов | страница: %d байт'
      % (len(ORDER), len(bundle), len(page.encode('utf-8'))))
print('готово:', os.path.join(OUT, 'vertikal-single.html'))

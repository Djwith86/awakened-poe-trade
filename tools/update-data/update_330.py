"""Add PoE 3.30 (Covens of Umbra) game data to awakened-poe-trade.

Sources: RePoE fork exports (3.29.3.6 -> 3.30.0.2.2) for names, translations,
gems and stat translations (incl. official trade stat ids).
Usage: python3 update_330.py <repoe_old_dir> <repoe_new_dir> <apt_data_dir>
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from statgen import build_stat, load_localized, LANGS  # noqa: E402

OLD, NEW, APT = (Path(p) for p in sys.argv[1:4])
LANG_DIR = {'en': '', 'ru': 'Russian', 'ko': 'Korean', 'cmn-Hant': 'Traditional Chinese'}
ICON_BASE = 'https://web.poecdn.com/image/'

# Unique -> base type (bases are not in RePoE; taken from 3.30 item listings)
UNIQUE_BASES = {
    "Bane of the Apostate": "Judgement Staff",
    "Corpse Rose": "Imbued Wand",
    "Dreadmaidens' Sacrament": "Basalt Flask",
    "Hide of the Vendigo": "Exquisite Leather",
    "Mantle of Dreams": "Twilight Regalia",
    "Ordered Fate": "Walnut Spirit Shield",
    "Putrid Seed": "Mycelium Core",
    "The Covetous Dark": "Eye Gouger",
    "The Sword of Ages": "Exquisite Blade",
    "Unwilling Embrace": "Bone Ring",
    "Veil of Flesh": "Callous Mask",
}
# Coin -> Soul Core and friends: siblings in the app are exchangeable without a tradeTag
NO_TRADE_TAG = {'Metadata/Items/Currency/CurrencyWishSupportGem'}
SKIP_NAMES = {'Corrupt'}  # placeholder-named Incursion currency, not real drops
EXCHANGE_CLASSES = {'StackableCurrency', 'MapFragment'}


def load(p):
    return json.load(open(p, encoding='utf-8'))


def ldir(root, lang):
    return root / LANG_DIR[lang] if LANG_DIR[lang] else root


def kebab(s):
    s = s.lower().replace("'", '')
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')


def icon(dds):
    return ICON_BASE + re.sub(r'\.dds$', '.png', dds) if dds else ''


def dumps(o):
    return json.dumps(o, ensure_ascii=False, separators=(',', ':'))


# ---------------------------------------------------------------- items

def read_ndjson(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def insert_sorted(rows, new_rows):
    """Insert rows keeping (namespace, lower(name)) order and same-ref adjacency."""
    for r in new_rows:
        key = (r['namespace'], r['refName'].lower())
        pos = len(rows)
        for i, x in enumerate(rows):
            if x['namespace'] == r['namespace'] and x['refName'] == r['refName']:
                pos = i + 1
                while pos < len(rows) and rows[pos]['namespace'] == r['namespace'] and rows[pos]['refName'] == r['refName']:
                    pos += 1
                break
            if (x['namespace'], x['refName'].lower()) > key:
                pos = i
                break
        rows.insert(pos, r)


def main():
    old_bases = load(OLD / 'base_items.json')
    new_bases = {lang: load(ldir(NEW, lang) / 'base_items.json') for lang in LANG_DIR}
    new_uniques = {lang: load(ldir(NEW, lang) / 'uniques.json') for lang in LANG_DIR}
    old_gems = load(OLD / 'gems.json')
    new_gems = {lang: load(ldir(NEW, lang) / 'gems.json') for lang in LANG_DIR}
    en_bases = new_bases['en']
    report = {'renamed': [], 'items': [], 'gems': [], 'uniques': [], 'stats': [], 'stat_merged': [], 'stat_conflicts': []}

    en_items = read_ndjson(APT / 'en' / 'items.ndjson')
    have = {(d['namespace'], d['refName']) for d in en_items}

    # 1. renamed bases (old English name present in app) -----------------
    renames = {}  # old refName -> metadata key
    for k, b in en_bases.items():
        if k in old_bases and old_bases[k]['name'] != b['name'] and ('ITEM', old_bases[k]['name']) in have:
            renames[old_bases[k]['name']] = k
            report['renamed'].append((old_bases[k]['name'], b['name']))

    # 2. new ITEM entries ---------------------------------------------------
    new_item_specs = []  # (key, kind)
    seen_names = set()
    for k, b in en_bases.items():
        if k in old_bases or b.get('release_state') != 'released':
            continue
        name = b['name']
        if name in SKIP_NAMES or name in seen_names or ('ITEM', name) in have:
            continue
        cls = b['item_class']
        if cls in EXCHANGE_CLASSES:
            kind = 'xchg_notag' if k in NO_TRADE_TAG else 'xchg'
        elif cls == 'Jewel':
            kind = 'jewel'
        elif cls == 'Viscera':
            kind = 'viscera'
        else:
            continue  # gems handled below, cocooned items are not tradable as-is
        seen_names.add(name)
        new_item_specs.append((k, kind))
        report['items'].append((name, cls, kind))

    # 3. new gems -------------------------------------------------------------
    gem_specs = []
    for gk, g in new_gems['en'].items():
        bi = g.get('base_item')
        if gk in old_gems or not bi or bi.get('release_state') != 'released':
            continue
        gem_specs.append(gk)
        report['gems'].append(g.get('display_name') or bi['display_name'])

    # 4. new uniques ----------------------------------------------------------
    old_unique_names = {u['name'] for u in load(OLD / 'uniques.json').values()}
    unique_specs = []  # (key, name)
    seen_u = set()
    for uk, u in new_uniques['en'].items():
        if u['name'] in old_unique_names or u['name'] in seen_u or u.get('is_alternate_art'):
            continue
        if u['name'] not in UNIQUE_BASES:
            print('WARN: no base for new unique', u['name'])
            continue
        seen_u.add(u['name'])
        unique_specs.append((uk, u['name']))
        report['uniques'].append((u['name'], UNIQUE_BASES[u['name']]))

    for lang in LANG_DIR:
        p = APT / lang / 'items.ndjson'
        rows = read_ndjson(p)
        lb = new_bases[lang]

        def lname(key):
            return (lb.get(key) or {}).get('name') or en_bases[key]['name']

        for r in rows:
            if r['namespace'] == 'ITEM' and r['refName'] in renames:
                key = renames[r['refName']]
                r['refName'] = en_bases[key]['name']
                r['name'] = lname(key)

        add = []
        for key, kind in new_item_specs:
            b = en_bases[key]
            row = {'name': lname(key), 'refName': b['name'], 'namespace': 'ITEM'}
            if kind == 'xchg':
                row['tradeTag'] = kebab(b['name'])
                row['exchangeable'] = True
            elif kind == 'xchg_notag':
                row['exchangeable'] = True
            elif kind == 'jewel':
                row['craftable'] = {'category': 'Jewel'}
            row['icon'] = icon(b['visual_identity']['dds_file'])
            if kind == 'viscera':
                row['w'] = b['inventory_width']
                row['h'] = b['inventory_height']
            add.append(row)

        lg = new_gems[lang]
        for gk in gem_specs:
            g, ge = lg.get(gk) or new_gems['en'][gk], new_gems['en'][gk]
            bi = ge['base_item']
            en_name = ge.get('display_name') or bi['display_name']
            row = {'name': g.get('display_name') or g['base_item']['display_name'], 'refName': en_name, 'namespace': 'GEM'}
            transfigured = en_name != bi['display_name']
            if transfigured:
                row['tradeDisc'] = 'alt_' + gk.rsplit('Alt', 1)[1].lower()
            row['icon'] = icon((en_bases.get(bi['id']) or {}).get('visual_identity', {}).get('dds_file'))
            gem = {}
            if transfigured:
                gem['transfigured'] = True
                gem['normalVariant'] = bi['display_name']
            gem['maxLevel'] = bi['max_level']
            row['gem'] = gem
            add.append(row)

        lu = new_uniques[lang]
        for uk, en_name in unique_specs:
            u = lu.get(uk) or new_uniques['en'][uk]
            if u.get('id') != new_uniques['en'][uk].get('id'):
                u = new_uniques['en'][uk]
            add.append({
                'name': u['name'], 'refName': en_name, 'namespace': 'UNIQUE',
                'unique': {'base': UNIQUE_BASES[en_name]},
                'icon': icon(new_uniques['en'][uk]['visual_identity']['dds_file']),
            })

        insert_sorted(rows, add)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            for r in rows:
                f.write(dumps(r) + '\n')

    # 5. stats ------------------------------------------------------------------
    t_new = load(NEW / 'stat_translations.json')
    t_old = load(OLD / 'stat_translations.json')
    old_ids = {tuple(e['ids']) for e in t_old}
    old_trade = {x['id'] for e in t_old for x in (e.get('trade_stats') or [])}

    en_stats = read_ndjson(APT / 'en' / 'stats.ndjson')
    app_trade = set()
    for d in en_stats:
        for s in (d['stats'] if 'resolve' in d else [d]):
            for v in s['trade']['ids'].values():
                app_trade.update(v)

    picked = []
    for e in t_new:
        ts = e.get('trade_stats') or []
        if not ts:
            continue
        missing = [x['id'] for x in ts if x['id'] not in app_trade]
        if not missing:
            continue
        if tuple(e['ids']) in old_ids and all(m in old_trade for m in missing):
            continue  # existed in 3.29 and upstream chose not to include it
        picked.append(e)

    for lang in LANG_DIR:
        p = APT / lang / 'stats.ndjson'
        rows = read_ndjson(p)
        loc = None if lang == 'en' else load_localized(ldir(NEW, lang) / 'stat_translations.json', lang)
        by_ref, by_matcher = {}, {}
        for i, d in enumerate(rows):
            for s in (d['stats'] if 'resolve' in d else [d]):
                by_ref.setdefault(s['ref'], (i, s, 'resolve' in d))
                for m in s['matchers']:
                    by_matcher.setdefault(m.get('advanced') or m['string'], (i, s))

        built = {}  # ref -> stat (merged across translation entries)
        for e in picked:
            s = build_stat(e, lang, None if lang == 'en' else loc.get(tuple(e['ids'])))
            if not s:
                continue
            if s['ref'] in built:
                b = built[s['ref']]
                for typ, ids in s['trade']['ids'].items():
                    b['trade']['ids'].setdefault(typ, [])
                    b['trade']['ids'][typ] += [x for x in ids if x not in b['trade']['ids'][typ]]
                for m in s['matchers']:
                    if m not in b['matchers']:
                        b['matchers'].append(m)
            else:
                built[s['ref']] = s

        new_rows = []
        for ref, s in built.items():
            if ref in by_ref:
                _, existing, _ = by_ref[ref]
                for typ, ids in s['trade']['ids'].items():
                    existing['trade']['ids'].setdefault(typ, [])
                    existing['trade']['ids'][typ] += [x for x in ids if x not in existing['trade']['ids'][typ]]
                if lang == 'en':
                    report['stat_merged'].append(ref)
                continue
            clash = [m['string'] for m in s['matchers'] if m['string'] in by_matcher]
            if clash:
                if lang == 'en':
                    report['stat_conflicts'].append((ref, clash, by_matcher[clash[0]][1]['ref']))
                s['matchers'] = [m for m in s['matchers'] if m['string'] not in by_matcher]
                if not s['matchers']:
                    continue
            for m in s['matchers']:
                by_matcher[m['string']] = (None, s)
            new_rows.append(s)
            if lang == 'en':
                report['stats'].append(ref)

        for s in sorted(new_rows, key=lambda s: s['ref']):
            pos = len(rows)
            for i, d in enumerate(rows):
                r = d['stats'][0]['ref'] if 'resolve' in d else d['ref']
                if r > s['ref']:
                    pos = i
                    break
            rows.insert(pos, s)
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            for r in rows:
                f.write(dumps(r) + '\n')

    json.dump(report, open('/home/claude/scripts/report.json', 'w'), indent=1, ensure_ascii=False)
    for k, v in report.items():
        print(k, len(v))


if __name__ == '__main__':
    main()

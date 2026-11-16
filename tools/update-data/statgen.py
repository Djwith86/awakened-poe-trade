"""Build awakened-poe-trade Stat entries from RePoE stat_translations entries."""
import re

LANGS = {'en': 'English', 'ru': 'Russian', 'ko': 'Korean', 'cmn-Hant': 'Traditional Chinese'}
DP_HANDLERS = {  # handlers for which upstream data marks the stat as decimal ("dp")
    'divide_by_one_hundred', 'divide_by_one_hundred_2dp_if_required', 'divide_by_one_hundred_2dp',
    'divide_by_one_thousand', 'divide_by_ten_1dp', 'divide_by_ten_1dp_if_required',
    'milliseconds_to_seconds_2dp', 'old_leech_percent', 'old_leech_permyriad',
    'per_minute_to_per_second_1dp', 'per_minute_to_per_second_2dp', 'per_minute_to_per_second_2dp_if_required',
}
_PH = re.compile(r'\{(\d+)(?::([^}]*))?\}')


def render(variant):
    """Return (text, all_handlers) with placeholders replaced by # or +#."""
    fmts = variant['format']
    used = []

    def sub(m):
        i = int(m.group(1))
        f = fmts[i] if i < len(fmts) else '#'
        used.append(i)
        if f == 'ignore':
            return ''
        return '#'  # app strips the sign: '+#' -> '#'
    text = _PH.sub(sub, variant['string'])
    handlers = [h for hs in variant.get('index_handlers', []) for h in (hs or [])]
    return text, used, handlers


def is_fixed(variant):
    conds = variant['condition']
    return bool(conds) and conds[0].get('min') is not None and conds[0].get('max') in (None, conds[0].get('min'))


def build_matchers(entry_lang):
    """entry_lang: list of variants for one language. Returns (matchers, dp, negated_main)."""
    matchers = []
    dp = False
    seen = set()
    for v in entry_lang:
        text, used, handlers = render(v)
        if any(h in DP_HANDLERS for h in handlers):
            dp = True
        has_ph = any(v['format'][i] != 'ignore' for i in used if i < len(v['format']))
        m = {'string': text}
        if 'negate' in handlers:
            m['negate'] = True
        if not has_ph and len(entry_lang) > 1 and '#' not in text:
            # a variant whose number is baked into the text
            c = v['condition'][0] if v['condition'] else {}
            val = c.get('min') if c.get('min') is not None else c.get('max')
            if val is not None:
                m['value'] = val
        key = (m['string'], m.get('negate'), m.get('value'))
        if key in seen or not text.strip():
            continue
        seen.add(key)
        matchers.append(m)
    # main matcher (non-negated, non-fixed) goes first, like upstream data
    matchers.sort(key=lambda m: (('value' in m), bool(m.get('negate'))))
    return matchers, dp


def trade_ids(entry):
    ids = {}
    for t in entry.get('trade_stats') or []:
        typ = t['id'].split('.', 1)[0]
        ids.setdefault(typ, [])
        if t['id'] not in ids[typ]:
            ids[typ].append(t['id'])
    return ids


def build_stat(entry, lang='en', loc_variants=None):
    ts = entry.get('trade_stats') or []
    if not ts:
        return None
    variants = entry['English'] if lang == 'en' else loc_variants
    if not variants:
        return None
    matchers, dp = build_matchers(variants)
    if not matchers:
        return None
    en_matchers, _ = build_matchers(entry['English'])
    ref = ts[0]['text']
    main = next((m for m in en_matchers if 'value' not in m), en_matchers[0])
    better = 1
    # main English form is the negated one -> "lower is better" style stat
    if main.get('negate'):
        better = -1
    stat = {'ref': ref}
    if dp:
        stat['dp'] = True
    stat['better'] = better
    stat['matchers'] = matchers
    stat['trade'] = {'ids': trade_ids(entry)}
    return stat


def load_localized(path, lang):
    import json
    out = {}
    for e in json.load(open(path)):
        v = e.get(LANGS[lang])
        if v:
            out[tuple(e['ids'])] = v
    return out

"""HTML parsing helpers — regex-based extraction for GitHub pages."""
import html
import re
from typing import Dict, List, Optional, Tuple


def _extract_token(t):
    m = re.search(r'name="authenticity_token"\s+value="([^"]+)"', t)
    return m.group(1) if m else None


def _extract_form_body(t, sub):
    p = r'<form[^>]+action="[^"]*' + re.escape(sub) + r'[^"]*"[^>]*>(.*?)</form>'
    m = re.search(p, t, re.S | re.I)
    return m.group(1) if m else None


def _extract_form(t, sub):
    p = r'(<form[^>]+action="[^"]*' + re.escape(sub) + r'[^"]*"[^>]*>)(.*?)</form>'
    m = re.search(p, t, re.S | re.I)
    return {"tag": m.group(1), "body": m.group(2)} if m else None


def _parse_hidden(form):
    r = {}
    for m in re.finditer(r"<input[^>]+>", form, re.I):
        tag = m.group(0)
        nm = re.search(r'name="([^"]+)"', tag, re.I)
        if not nm:
            continue
        vm = re.search(r'value="([^"]*)"', tag, re.I)
        r[nm.group(1)] = html.unescape(vm.group(1)) if vm else ""
    return r


def _tag_attrs(tag):
    a = {}
    for m in re.finditer(r'([a-zA-Z0-9_:\-]+)="([^"]*)"', tag):
        a[m.group(1).lower()] = html.unescape(m.group(2))
    return a


def _find_select_first(t, name):
    p = r'<select[^>]+name="' + re.escape(name) + r'"[^>]*>(.*?)</select>'
    m = re.search(p, t, re.S | re.I)
    if not m:
        return None
    om = re.search(r'<option[^>]+value="([^"]+)"', m.group(1), re.I)
    return html.unescape(om.group(1)) if om else None


def _find_select_names(t, sub):
    ns = []
    for m in re.finditer(r"<select[^>]+>", t, re.I):
        a = _tag_attrs(m.group(0))
        n = a.get("name", "")
        if sub.lower() in n.lower():
            ns.append(n)
    return ns


def _find_select_option_label(t, lsub):
    for sm in re.finditer(r"<select[^>]*>.*?</select>", t, re.S | re.I):
        st = re.search(r"<select[^>]*>", sm.group(0), re.I)
        if not st:
            continue
        sa = _tag_attrs(st.group(0))
        sn = sa.get("name")
        if not sn:
            continue
        for om in re.finditer(r"<option[^>]*>.*?</option>", sm.group(0), re.S | re.I):
            ot = re.search(r"<option[^>]*>", om.group(0), re.I)
            if not ot:
                continue
            oa = _tag_attrs(ot.group(0))
            ov = oa.get("value", "")
            otx = html.unescape(re.sub(r"<[^>]+>", "", om.group(0))).strip()
            if lsub.lower() in otx.lower():
                return {"name": sn, "value": ov}
    return None


def _get_input_val(t, field_name):
    """Extract value of a form field (input/textarea/select) by name."""
    # 1. Input tags (skip disabled ones)
    for m in re.finditer(r'<input\b[^>]*>', t, re.I):
        tag = m.group(0)
        nm = re.search(r'name="([^"]*)"', tag, re.I)
        if not nm or nm.group(1) != field_name:
            continue
        if re.search(r'\bdisabled\b', tag, re.I):
            continue
        vm = re.search(r'value="([^"]*)"', tag, re.I)
        return html.unescape(vm.group(1)).strip() if vm else ""
    # 2. Textarea
    pat = r'<textarea\b[^>]*name="' + re.escape(field_name) + r'"[^>]*>(.*?)</textarea>'
    m = re.search(pat, t, re.S | re.I)
    if m:
        return html.unescape(m.group(1)).strip()
    # 3. Select -> selected option (skip disabled selects)
    for sm in re.finditer(r'<select\b([^>]*)>(.*?)</select>', t, re.S | re.I):
        attrs = sm.group(1)
        nm = re.search(r'name="([^"]*)"', attrs, re.I)
        if not nm or nm.group(1) != field_name:
            continue
        if re.search(r'\bdisabled\b', attrs, re.I):
            continue
        opts = sm.group(2)
        for om in re.finditer(r'<option\b([^>]*)>', opts, re.I):
            oa = om.group(1)
            if 'selected' in oa.lower():
                vm = re.search(r'value="([^"]*)"', oa, re.I)
                if vm:
                    return html.unescape(vm.group(1)).strip()
    return ""


def _action_menu_vals(t, fname):
    mk = f'name="{fname}"'
    st = t.find(mk)
    if st == -1:
        return []
    w = t[st:st + 8000]
    r = []
    for m in re.finditer(
            r'<button[^>]+data-value="([^"]+)"[^>]*>.*?'
            r'<span[^>]*ActionListItem-label[^>]*>(.*?)</span>', w, re.S | re.I):
        v = html.unescape(m.group(1)).strip()
        l = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        if v:
            r.append((v, l))
    return r


def _action_menu_by_label(t, fname, lsub):
    for v, l in _action_menu_vals(t, fname):
        if lsub.lower() in l.lower():
            return v
    return None


def _action_menu_first(t, fname):
    vs = _action_menu_vals(t, fname)
    return vs[0][0] if vs else None


def _get_scoped_csrf(html_text: str, form_action_sub: str) -> Optional[str]:
    """Extract Scoped-CSRF-Token from a js-data-url-csrf hidden input
    inside a form whose action contains `form_action_sub`."""
    form_body = _extract_form_body(html_text, form_action_sub)
    if not form_body:
        return None
    for im in re.finditer(r'<input[^>]+>', form_body, re.I):
        tag = im.group(0)
        if 'js-data-url-csrf' not in tag:
            continue
        vm = re.search(r'value="([^"]+)"', tag)
        if vm:
            return vm.group(1)
    return None


def _get_fetch_nonce(html_text: str) -> str:
    """Extract X-Fetch-Nonce from <meta name="fetch-nonce">."""
    m = re.search(r'<meta\s+name="fetch-nonce"\s+content="([^"]+)"',
                  html_text, re.I)
    return m.group(1) if m else ""


def _get_release_version(html_text: str) -> str:
    """Extract X-GitHub-Client-Version from <meta name="release">."""
    m = re.search(r'<meta\s+name="release"\s+content="([^"]+)"',
                  html_text, re.I)
    return m.group(1) if m else ""


def _api_headers(csrf_token: str, nonce: str, release: str) -> dict:
    """Build the headers GitHub's JS uses for its internal API calls."""
    h = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Scoped-CSRF-Token": csrf_token,
    }
    if nonce:
        h["X-Fetch-Nonce"] = nonce
    if release:
        h["X-GitHub-Client-Version"] = release
    return h

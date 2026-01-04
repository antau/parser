# app.py
# Version: v2.2-html (handles first store with or without leading <br>)

import re
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components

APP_VERSION = "v2.2-html"

st.set_page_config(layout="wide")
st.title("TCGPlayer Orders (HTML Table)")
st.caption(f"App version: {APP_VERSION}")

raw_text = st.text_area("Paste order list here:", height=320)

def parse_orders(raw: str):
    raw = html_lib.unescape(raw)

    # Remove span tags but keep text
    raw = re.sub(r"</?span[^>]*>", "", raw, flags=re.IGNORECASE)

    # Store/total can start either:
    # - at the beginning of the text, OR
    # - right after a <br>
    store_total = re.findall(
        r"(?:^|<br\s*/?>)\s*([^<$\n\r]+?)\s*\$(\d+\.\d{2})",
        raw,
        flags=re.IGNORECASE | re.MULTILINE,
    )

    # Extract orderhistory URLs
    urls = re.findall(
        r'https?://store\.tcgplayer\.com/myaccount/orderhistory\?SearchString=[A-Z0-9\-]+',
        raw,
        flags=re.IGNORECASE,
    )

    n = min(len(store_total), len(urls))
    orders = []
    for i in range(n):
        store = store_total[i][0].strip()
        total = f"${store_total[i][1]}"
        url = urls[i]
        orders.append({"store": store, "total": total, "url": url})

    return orders

def build_html_table(orders):
    rows = []
    for o in orders:
        store = html_lib.escape(o["store"])
        total = html_lib.escape(o["total"])
        url = html_lib.escape(o["url"], quote=True)

        rows.append(
            f'<tr>'
            f'<td><a href="{url}" target="_blank" rel="noopener noreferrer">{store}</a></td>'
            f'<td style="text-align:right;">{total}</td>'
            f'</tr>'
        )

    html_doc = (
        '<style>'
        'table.tcg{font-family:Arial,sans-serif;font-size:10px;border-collapse:collapse;width:100%;}'
        '.tcg th,.tcg td{border:1px solid #ddd;padding:6px 8px;}'
        '.tcg th{background:#f6f6f6;text-align:left;}'
        '.tcg tr:nth-child(even){background:#fafafa;}'
        '.tcg a{text-decoration:none;}'
        '.tcg a:hover{text-decoration:underline;}'
        '</style>'
        '<table class="tcg">'
        '<thead><tr><th>Store Name</th><th>Order Total</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        '</table>'
    )
    return html_doc

if raw_text.strip():
    orders = parse_orders(raw_text)

    if not orders:
        st.error("No orders detected. Make sure your input contains lines like: StoreName $12.34")
    else:
        components.html(build_html_table(orders), height=520, scrolling=True)

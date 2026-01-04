# app.py
# Version: v2.0-html (HTML table renderer)

import re
import html as html_lib
import streamlit as st

APP_VERSION = "v2.0-html"

st.set_page_config(layout="wide")
st.title("TCGPlayer Orders (HTML Table)")
st.caption(f"App version: {APP_VERSION}")

raw_text = st.text_area("Paste order list here:", height=320)

def parse_orders(raw: str):
    """
    Returns list of dicts: {"store": str, "total": str, "url": str}
    Robust against extra tags/spans and Gmail formatting.
    """
    # Decode entities (&amp; etc.) so regex works consistently
    raw = html_lib.unescape(raw)

    # Convert <br> to newlines to help matching store/total lines
    raw_nl = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)

    # Remove span tags but keep their text content
    raw_nl = re.sub(r"</?span[^>]*>", "", raw_nl, flags=re.IGNORECASE)

    # --- Extract store + total from lines like: Store Name $12.34
    store_total = []
    for line in raw_nl.splitlines():
        line = line.strip()
        m = re.match(r"(.+?)\s+\$(\d+\.\d{2})$", line)
        if m:
            store_total.append((m.group(1).strip(), f"${m.group(2)}"))

    # --- Extract order history URLs
    # We specifically capture the orderhistory SearchString URL.
    urls = re.findall(
        r'https?://store\.tcgplayer\.com/myaccount/orderhistory\?SearchString=[A-Z0-9\-]+',
        raw_nl,
        flags=re.IGNORECASE,
    )

    # Pair them in order (they appear in order in the input)
    n = min(len(store_total), len(urls))
    orders = []
    for i in range(n):
        store, total = store_total[i]
        url = urls[i]
        orders.append({"store": store, "total": total, "url": url})

    return orders

def render_html_table(orders):
    # Basic HTML escaping for store names/totals to prevent broken markup
    rows_html = []
    for o in orders:
        store = html_lib.escape(o["store"])
        total = html_lib.escape(o["total"])
        url = html_lib.escape(o["url"], quote=True)

        rows_html.append(
            f"""
            <tr>
              <td><a href="{url}" target="_blank" rel="noopener noreferrer">{store}</a></td>
              <td style="text-align:right;">{total}</td>
            </tr>
            """
        )

    table_html = f"""
    <style>
      .tcg-table {{
        font-family: Arial, sans-serif;
        font-size: 10px;
        border-collapse: collapse;
        width: 100%;
      }}
      .tcg-table th, .tcg-table td {{
        border: 1px solid #ddd;
        padding: 6px 8px;
        vertical-align: top;
      }}
      .tcg-table th {{
        background: #f6f6f6;
        text-align: left;
      }}
      .tcg-table tr:nth-child(even) {{
        background: #fafafa;
      }}
      .tcg-table a {{
        text-decoration: none;
      }}
      .tcg-table a:hover {{
        text-decoration: underline;
      }}
    </style>

    <table class="tcg-table">
      <thead>
        <tr>
          <th>Store Name</th>
          <th>Order Total</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows_html)}
      </tbody>
    </table>
    """
    return table_html

if raw_text.strip():
    orders = parse_orders(raw_text)
    if not orders:
        st.error("No orders detected. Check that your input includes lines like: <br>StoreName $12.34")
    else:
        st.markdown(render_html_table(orders), unsafe_allow_html=True)

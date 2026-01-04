import streamlit as st
import pandas as pd
import re
import html

# =========================
# App Version
# =========================
APP_VERSION = "v1.2"

st.set_page_config(layout="wide")
st.title("TCGPlayer Orders")
st.caption(f"App version: {APP_VERSION}")

raw_text = st.text_area("Paste order list:", height=400)

def parse_orders(text: str):
    text = html.unescape(text)

    # Normalize <br> to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Remove span tags but keep text
    text = re.sub(r"</?span[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove all remaining HTML
    text = re.sub(r"<[^>]+>", "", text)

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    rows = []
    i = 0
    while i < len(lines):
        # Match: Store Name $12.34
        m = re.match(r"(.+?)\s+\$(\d+\.\d{2})$", lines[i])
        if not m:
            i += 1
            continue

        store, total = m.groups()

        # Find Order Number in the following lines
        order_id = None
        for j in range(i + 1, min(i + 4, len(lines))):
            oid = re.search(r"Order Number:\s*([A-Z0-9\-]+)", lines[j])
            if oid:
                order_id = oid.group(1)
                break

        url = (
            "https://store.tcgplayer.com/myaccount/orderhistory"
            f"?SearchString={order_id}"
            if order_id else ""
        )

        rows.append({
            "Store Name": store,
            "Order URL": url,
            "Order Total": f"${total}"
        })

        i += 1

    return rows

if raw_text.strip():
    data = parse_orders(raw_text)

    if data:
        df = pd.DataFrame(data)

        st.dataframe(
            df,
            hide_index=True,              # no 0,1,2 column
            use_container_width=True,
            column_config={
                "Order URL": st.column_config.LinkColumn(
                    "Store Name",
                    display_text="View Order"
                )
            }
        )
    else:
        st.warning("No orders found.")

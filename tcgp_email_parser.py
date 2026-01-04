import streamlit as st
import pandas as pd
import re
import html

st.set_page_config(layout="wide")
st.title("TCGPlayer Order Summary")

raw_text = st.text_area(
    "Paste your order list here:",
    height=400
)

def strip_all_html(text: str) -> str:
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text)

def parse_orders(text: str):
    clean_text = strip_all_html(text)

    # Matches: Store Name $12.34
    pattern = re.compile(r"(.+?)\s+\$(\d+\.\d{2})")

    orders = []
    for line in clean_text.splitlines():
        match = pattern.search(line)
        if match:
            store = match.group(1).strip()
            total = match.group(2)

            url = (
                "https://store.tcgplayer.com/myaccount/orderhistory"
                f"?SearchString={store.replace(' ', '%20')}"
            )

            orders.append({
                "Store Name": f"[{store}]({url})",
                "Order Total": f"${total}"
            })

    return orders

if raw_text.strip():
    orders = parse_orders(raw_text)

    if orders:
        df = pd.DataFrame(orders)

        st.markdown(
            """
            <style>
            div[data-testid="stDataFrame"] * {
                font-family: Arial, sans-serif;
                font-size: 10pt;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.dataframe(
            df,
            use_container_width=True
        )
    else:
        st.warning("No orders found. Please check the input format.")

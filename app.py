# app.py
# Version: v1.6

import re
import pandas as pd
import streamlit as st

# -----------------------
# Page config
# -----------------------
st.set_page_config(layout="wide")
st.caption("App version: v1.6")

# -----------------------
# Global CSS (Arial, size 10)
# -----------------------
st.markdown(
    """
    <style>
    * {
        font-family: Arial, sans-serif;
        font-size: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Input
# -----------------------
raw_text = st.text_area(
    "Paste order list here:",
    height=300,
)

# -----------------------
# Parse function
# -----------------------
def parse_orders(text: str):
    results = []

    pattern = re.compile(
        r"<br>\s*([^<$]+?)\s*\$(\d+\.\d{2}).*?"
        r"SearchString=([A-Z0-9-]+)",
        re.DOTALL,
    )

    for store, total, order_id in pattern.findall(text):
        results.append(
            {
                "Store Name": store.strip(),
                "Store Link": f"https://store.tcgplayer.com/myaccount/orderhistory?SearchString={order_id}",
                "Order Total": f"${total}",
            }
        )

    return pd.DataFrame(results)


# -----------------------
# Output
# -----------------------
if raw_text.strip():
    df = parse_orders(raw_text)

    if df.empty:
        st.error("No orders detected. Check input format.")
    else:
        st.dataframe(
            df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Store Name": st.column_config.LinkColumn(
                    "Store Name",
                    url_column="Store Link",
                ),
                "Store Link": None,  # hide helper column
                "Order Total": "Order Total",
            },
        )

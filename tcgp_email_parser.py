import streamlit as st
import re
import html

st.set_page_config(layout="wide")
st.title("TCGPlayer Orders")

raw_text = st.text_area(
    "Paste your order list here:",
    height=400
)

def clean_html(text):
    # Remove span tags and their contents formatting
    text = re.sub(r"<span.*?>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"</span>", "", text, flags=re.IGNORECASE)
    return html.unescape(text)

def parse_orders(text):
    text = clean_html(text)

    # Pattern:
    # <br>StoreName $OrderTotal
    # ... href="https://store.tcgplayer.com/myaccount/orderhistory?SearchString=..."
    pattern = re.compile(
        r"<br>\s*([^<$]+?)\s*\$(\d+\.\d{2}).*?"
        r'href="(https://store\.tcgplayer\.com/myaccount/orderhistory\?SearchString=[^"]+)"',
        re.IGNORECASE | re.DOTALL
    )

    results = []
    for store, total, url in pattern.findall(text):
        results.append({
            "store": store.strip(),
            "total": f"${total}",
            "url": url
        })

    return results

if raw_text.strip():
    orders = parse_orders(raw_text)

    if orders:
        table_html = """
        <style>
            table {
                font-family: Arial, sans-serif;
                font-size: 10pt;
                border-collapse: collapse;
                width: 100%;
            }
            th, td {
                border: 1px solid #cccccc;
                padding: 4px 6px;
                text-align: left;
            }
            th {
                background-color: #f2f2f2;
            }
            a {
                color: #0066cc;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
        <table>
            <tr>
                <th>Store Name</th>
                <th>Order Total</th>
            </tr>
        """

        for o in orders:
            table_html += f"""
            <tr>
                <td><a href="{o['url']}" target="_blank">{o['store']}</a></td>
                <td>{o['total']}</td>
            </tr>
            """

        table_html += "</table>"

        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.warning("No orders found. Check the pasted format.")

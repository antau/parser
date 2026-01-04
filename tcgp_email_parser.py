import streamlit.components.v1 as components

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

    components.html(
        table_html,
        height=700,
        scrolling=True
    )

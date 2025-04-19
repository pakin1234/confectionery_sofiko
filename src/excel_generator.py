import json
import pandas as pd

def json_to_xlsx():
    with open("orders.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    rows = []
    for user_id, orders in data.items():
        for order in orders:
            row = {"Id клиента": user_id}
            row["Номер заказа"] = order["order_id"]
            row["Товар"] = order["item"]
            row["Вид товара"] = order["type"]
            row["Цена"] = order["price"]
            row["Оплачено"] = order["paid"]
            row["Дата заказа"] = order["date"]
            rows.append(row)
    rows.sort(key=lambda x: (x["Id клиента"], x.get("Дата заказа", "")))
    df = pd.DataFrame(rows)
    df.to_excel("orders.xlsx", index=False)

    print("Excel-файл создан: orders.xlsx")

print(pd.__version__)
json_to_xlsx()
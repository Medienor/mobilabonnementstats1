import requests
import json
from weds import webflow_bearer_token
from statistics import mean, median
from datetime import datetime

def fetch_items(collection_id, offset=0):
    url = f"https://api.webflow.com/v2/collections/{collection_id}/items?limit=100&offset={offset}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    response = requests.get(url, headers=headers)
    return json.loads(response.text)

def fetch_mobiloperators():
    url = "https://api.webflow.com/v2/collections/6662d0070fad018b334db523/items"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    response = requests.get(url, headers=headers)
    data = json.loads(response.text)
    return {item['id']: {'name': item['fieldData']['name'], 'slug': item['fieldData']['slug']} for item in data['items']}

def update_stats(contract_count, mobiloperator_count, paragraph, avg_price_10, avg_price_100, h1, dato):
    url = "https://api.webflow.com/v2/collections/66b3eb1589ff4ef9005da526/items/66b3eb26ab5d3a893f2acd9e/live"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    payload = {
        "fieldData": {
            "name": "Stats",
            "slug": "stats",
            "antall-avtaler": str(contract_count),
            "antall-operatorer": str(mobiloperator_count),
            "paragraf-billig-dyr-2": f"<p>{paragraph}</p>",
            "avg-price-10": str(avg_price_10),
            "avg-price-100": str(avg_price_100),
            "h1": h1,
            "dato": dato
        }
    }
    response = requests.patch(url, json=payload, headers=headers)
    return response.json()

def clear_price_status(operator_id):
    url = f"https://api.webflow.com/v2/collections/6662d0070fad018b334db523/items/{operator_id}/live"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    payload = {
        "fieldData": {
            "pris-billig": "",
            "pris-dyr": ""
        }
    }
    response = requests.patch(url, json=payload, headers=headers)
    return response.json()

def update_mobiloperator(operator_id, is_cheapest, name):
    url = f"https://api.webflow.com/v2/collections/6662d0070fad018b334db523/items/{operator_id}/live"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {webflow_bearer_token}"
    }
    payload = {
        "fieldData": {}
    }
    if is_cheapest:
        payload["fieldData"]["pris-billig"] = f"{name} er kåret til Norges billigste mobiloperatør"
    else:
        payload["fieldData"]["pris-dyr"] = f"{name} er kåret til Norges dyreste mobiloperatør"
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.json()

def process_items():
    offset = 0
    contract_count = 0
    mobiloperator_prices = {}
    non_business_prices = {}
    prices_10gb = []
    prices_100gb = []
    mobiloperator_names = fetch_mobiloperators()

    # Clear price status for all operators
    for operator_id in mobiloperator_names:
        clear_result = clear_price_status(operator_id)
        print(f"Cleared price status for {mobiloperator_names[operator_id]['name']}: {clear_result}")

    while True:
        data = fetch_items("6660c15ec77f5270c0a534d2", offset)
        items = data.get('items', [])
        
        if not items:
            break

        for item in items:
            contract_count += 1
            mobiloperator = item['fieldData'].get('mobiloperator')
            price = item['fieldData'].get('pris')
            mobildata = item['fieldData'].get('mobildata')
            is_bedriftsabonnement = item['fieldData'].get('bedriftsabonnement', False)
            
            if mobiloperator and price:
                if mobiloperator not in mobiloperator_prices:
                    mobiloperator_prices[mobiloperator] = []
                mobiloperator_prices[mobiloperator].append(price)
            
            if not is_bedriftsabonnement:
                if mobiloperator not in non_business_prices:
                    non_business_prices[mobiloperator] = []
                non_business_prices[mobiloperator].append(price)
                
                if mobildata == '10' and price:
                    prices_10gb.append(price)
                elif mobildata == '100' and price:
                    prices_100gb.append(price)

        offset += 100

    # Calculate average prices for non-business contracts
    avg_non_business_prices = {op: mean(prices) for op, prices in non_business_prices.items()}
    cheapest_op = min(avg_non_business_prices, key=avg_non_business_prices.get)
    most_expensive_op = max(avg_non_business_prices, key=avg_non_business_prices.get)

    # Update the cheapest and most expensive mobiloperators
    cheapest_update = update_mobiloperator(cheapest_op, True, mobiloperator_names[cheapest_op]["name"])
    expensive_update = update_mobiloperator(most_expensive_op, False, mobiloperator_names[most_expensive_op]["name"])

    print("Cheapest operator update result:", cheapest_update)
    print("Most expensive operator update result:", expensive_update)

    # Calculate percentage difference
    price_diff_percent = ((avg_non_business_prices[most_expensive_op] - avg_non_business_prices[cheapest_op]) / avg_non_business_prices[most_expensive_op]) * 100

    # Create the paragraph with linked company names
    cheapest_op_link = f'<a href="/mobiltelefoni/mobiloperatorer/{mobiloperator_names[cheapest_op]["slug"]}">{mobiloperator_names[cheapest_op]["name"]}</a>'
    most_expensive_op_link = f'<a href="/mobiltelefoni/mobiloperatorer/{mobiloperator_names[most_expensive_op]["slug"]}">{mobiloperator_names[most_expensive_op]["name"]}</a>'

    paragraph = (f"Mobiloperatøren {cheapest_op_link} er den som har de billigste avtalene på privatmarkedet mobilabonnement, "
                 f"de er faktisk {price_diff_percent:.1f}% billigere enn den dyreste leverandøren på privatmarkedet mobiltelefoni "
                 f"som er {most_expensive_op_link}.")

    # Calculate median prices for 10GB and 100GB
    avg_price_10 = median(prices_10gb) if prices_10gb else 0
    avg_price_100 = median(prices_100gb) if prices_100gb else 0

    # Create h1 with current month and year
    current_date = datetime.now()
    month_name = current_date.strftime("%B").lower()  # Convert to lowercase
    year = current_date.year
    h1 = f"Alle mobiloperatører {month_name} {year}"

    # Create dato string
    dato = f"{month_name} {year}"

    print(f"Total number of contracts: {contract_count}")
    print(f"Number of unique 'mobiloperator': {len(mobiloperator_prices)}")
    print(f"Paragraph: {paragraph}")
    print(f"Median price for 10GB (non-business): {avg_price_10}")
    print(f"Median price for 100GB (non-business): {avg_price_100}")
    print(f"H1: {h1}")
    print(f"Dato: {dato}")

    # Update the stats in Webflow
    update_result = update_stats(contract_count, len(mobiloperator_prices), paragraph, avg_price_10, avg_price_100, h1, dato)
    print("Update result:", update_result)

if __name__ == "__main__":
    process_items()
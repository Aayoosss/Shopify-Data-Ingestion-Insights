# shopify.py
import requests
import os

API_VERSION = "2023-07" # Use a stable API version

def get_shopify_data(tenant_shop_name: str, tenant_token: str, resource: str):
    """
    Fetches data from the Shopify API.
    - tenant_shop_name: The name of the Shopify store (e.g., 'your-store-name').
    - tenant_token: The access token for the specific store.
    - resource: The API endpoint (e.g., "customers", "products").
    """
    headers = {
        "X-Shopify-Access-Token": tenant_token,
        "Content-Type": "application/json"
    }
    # Dynamically build the URL using the shop name from the database
    url = f"https://{tenant_shop_name}.myshopify.com/admin/api/{API_VERSION}/{resource}.json"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Shopify: {e}")
        raise
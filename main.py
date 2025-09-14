from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import Base, engine, get_db
from models import Tenant, Customer, Product, ProductVariant, Order, OrderLineItem
import shopify
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create all database tables based on the models
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/update_tenant")
def update_tenant(shop_name: str, access_token: str, db: Session = Depends(get_db)):
    """
    Finds a tenant by shop_name and updates their access token.
    If the tenant doesn't exist, it creates a new one.
    """
    # Query for the existing tenant by shop_name
    tenant = db.query(Tenant).filter(Tenant.shop_name == shop_name).first()

    if tenant:
        # If the tenant exists, update the access token.
        # This explicit update will trigger the 'updated_at' timestamp.
        tenant.access_token = access_token
        db.add(tenant)
        message = "Tenant access token updated successfully."
    else:
        # If the tenant doesn't exist, create a new record.
        new_tenant = Tenant(shop_name=shop_name, access_token=access_token)
        db.add(new_tenant)
        message = "New tenant created successfully."

    db.commit()
    return {"message": message}

@app.post("/ingest/customers/{tenant_id}")
def ingest_customers(tenant_id: int, db: Session = Depends(get_db)):
    """Ingests customer data from Shopify for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        # Pass the shop_name from the tenant record to the Shopify client
        data = shopify.get_shopify_data(tenant.shop_name, tenant.access_token, "customers")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    customers_data = data.get("customers", [])
    for customer_json in customers_data:
        shopify_id = customer_json.get("id")
        
        # Check for existing customer to perform an upsert
        db_customer = db.query(Customer).filter(
            Customer.shopify_customer_id == shopify_id,
            Customer.tenant_id == tenant_id
        ).first()

        if db_customer:
            # Update existing record
            db_customer.first_name = customer_json.get('first_name')
            db_customer.last_name = customer_json.get('last_name')
            db_customer.email = customer_json.get('email')
            db_customer.phone = customer_json.get('phone')
        else:
            # Create new record
            new_customer = Customer(
                tenant_id=tenant_id,
                shopify_customer_id=shopify_id,
                first_name=customer_json.get('first_name'),
                last_name=customer_json.get('last_name'),
                email=customer_json.get('email'),
                phone=customer_json.get('phone')
            )
            db.add(new_customer)
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A unique constraint was violated.")
        
    return {"message": f"Successfully ingested {len(customers_data)} customers."}
    
@app.post("/ingest/products/{tenant_id}")
def ingest_products(tenant_id: int, db: Session = Depends(get_db)):
    """Ingests product and variant data from Shopify for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        # Pass the shop_name and access_token to the Shopify client
        data = shopify.get_shopify_data(tenant.shop_name, tenant.access_token, "products")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    products_data = data.get("products", [])
    for product_json in products_data:
        shopify_product_id = product_json.get("id")
        
        # Upsert the product
        db_product = db.query(Product).filter(
            Product.shopify_product_id == shopify_product_id,
            Product.tenant_id == tenant_id
        ).first()

        if db_product:
            db_product.title = product_json.get('title')
            db_product.vendor = product_json.get('vendor')
            db_product.product_type = product_json.get('product_type')
        else:
            new_product = Product(
                tenant_id=tenant_id,
                shopify_product_id=shopify_product_id,
                title=product_json.get('title'),
                vendor=product_json.get('vendor'),
                product_type=product_json.get('product_type')
            )
            db.add(new_product)
            db.flush() # Flush to get the new product's ID

        product_id_to_link = db_product.id if db_product else new_product.id
        
        # Upsert the product's variants
        variants_data = product_json.get("variants", [])
        for variant_json in variants_data:
            shopify_variant_id = variant_json.get("id")
            db_variant = db.query(ProductVariant).filter(
                ProductVariant.shopify_variant_id == shopify_variant_id
            ).first()

            if db_variant:
                db_variant.title = variant_json.get('title')
                db_variant.price = variant_json.get('price')
                db_variant.sku = variant_json.get('sku')
                db_variant.weight = variant_json.get('weight')
                db_variant.weight_unit = variant_json.get('weight_unit')
            else:
                new_variant = ProductVariant(
                    product_id=product_id_to_link,
                    shopify_variant_id=shopify_variant_id,
                    title=variant_json.get('title'),
                    price=variant_json.get('price'),
                    sku=variant_json.get('sku'),
                    weight=variant_json.get('weight'),
                    weight_unit=variant_json.get('weight_unit')
                )
                db.add(new_variant)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A unique constraint was violated.")

    return {"message": f"Successfully ingested {len(products_data)} products and their variants."}

@app.post("/ingest/orders/{tenant_id}")
def ingest_orders(tenant_id: int, db: Session = Depends(get_db)):
    """Ingests order and line item data from Shopify for a specific tenant."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    try:
        # Pass the shop_name and access_token to the Shopify client
        data = shopify.get_shopify_data(tenant.shop_name, tenant.access_token, "orders")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    orders_data = data.get("orders", [])
    for order_json in orders_data:
        shopify_order_id = order_json.get("id")
        
        # Find local customer_id
        customer_id_from_db = None
        customer_json = order_json.get("customer")
        if customer_json:
            shopify_customer_id = customer_json.get("id")
            db_customer = db.query(Customer).filter(
                Customer.shopify_customer_id == shopify_customer_id,
                Customer.tenant_id == tenant_id
            ).first()
            if db_customer:
                customer_id_from_db = db_customer.id
        
        # Upsert the order
        db_order = db.query(Order).filter(
            Order.shopify_order_id == shopify_order_id,
            Order.tenant_id == tenant_id
        ).first()

        if db_order:
            db_order.total_price = order_json.get('total_price')
            db_order.currency = order_json.get('currency')
            db_order.customer_id = customer_id_from_db
        else:
            new_order = Order(
                tenant_id=tenant_id,
                customer_id=customer_id_from_db,
                shopify_order_id=shopify_order_id,
                total_price=order_json.get('total_price'),
                currency=order_json.get('currency'),
            )
            db.add(new_order)
            db.flush()

        order_id_to_link = db_order.id if db_order else new_order.id

        # Upsert line items
        line_items_data = order_json.get("line_items", [])
        for line_item_json in line_items_data:
            shopify_variant_id = line_item_json.get("variant_id")
            db_variant = db.query(ProductVariant).filter(
                ProductVariant.shopify_variant_id == shopify_variant_id
            ).first()

            if db_variant:
                db_line_item = db.query(OrderLineItem).filter(
                    OrderLineItem.order_id == order_id_to_link,
                    OrderLineItem.variant_id == db_variant.id
                ).first()
                
                if db_line_item:
                    db_line_item.quantity = line_item_json.get('quantity')
                    db_line_item.price = line_item_json.get('price')
                else:
                    new_line_item = OrderLineItem(
                        order_id=order_id_to_link,
                        variant_id=db_variant.id,
                        quantity=line_item_json.get('quantity'),
                        price=line_item_json.get('price')
                    )
                    db.add(new_line_item)
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A unique constraint was violated.")

    return {"message": f"Successfully ingested {len(orders_data)} orders."}
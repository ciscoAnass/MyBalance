#!/usr/bin/env python3
"""
Flask Product Inventory Management Application
A clean, professional web app for managing product inventory using CSV files.
Designed for users 50+ with minimal colors and intuitive interface.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import csv
import os
from datetime import datetime
import json

app = Flask(__name__)

# Configuration
CSV_FILE = 'products.csv'
CSV_HEADERS = ['id', 'name', 'serial_number', 'provider', 'buy_price', 'sell_price', 'benefit', 'date', 'sell_date']

def ensure_csv_exists():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

def load_products():
    """Load all products from CSV file"""
    ensure_csv_exists()
    products = []
    try:
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert numeric fields
                row['id'] = int(row['id']) if row['id'] else 0
                row['buy_price'] = float(row['buy_price']) if row['buy_price'] else 0.0
                row['sell_price'] = float(row['sell_price']) if row['sell_price'] else 0.0
                row['benefit'] = float(row['benefit']) if row['benefit'] else 0.0
                # Handle sell_date field for backward compatibility
                if 'sell_date' not in row:
                    row['sell_date'] = ''
                products.append(row)
    except FileNotFoundError:
        pass
    return products

def save_products(products):
    """Save all products to CSV file"""
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(products)

def get_next_id():
    """Get the next available ID"""
    products = load_products()
    if not products:
        return 1
    return max(int(p['id']) for p in products) + 1

def calculate_benefit(buy_price, sell_price):
    """Calculate benefit from buy and sell prices"""
    buy = float(buy_price) if buy_price else 0.0
    sell = float(sell_price) if sell_price else 0.0
    # Only calculate benefit if item is actually sold (sell_price > 0)
    return sell - buy if sell > 0 else 0.0

def get_unique_providers():
    """Get list of unique providers from existing products"""
    products = load_products()
    providers = set()
    for product in products:
        if product['provider'] and product['provider'].strip():
            providers.add(product['provider'].strip())
    return sorted(list(providers))

@app.route('/')
def index():
    """Main page"""
    products = load_products()
    providers = get_unique_providers()
    return render_template('index.html', products=products, providers=providers)

@app.route('/api/products')
def api_products():
    """API endpoint to get all products"""
    products = load_products()
    return jsonify(products)

@app.route('/api/products/add', methods=['POST'])
def add_product():
    """Add new product(s)"""
    data = request.json
    
    name = data.get('name', '').strip()
    serial_number = data.get('serial_number', '').strip()
    provider = data.get('provider', '').strip()
    buy_price = float(data.get('buy_price', 0))
    sell_price = float(data.get('sell_price', 0)) if data.get('sell_price') else 0
    quantity = int(data.get('quantity', 1))
    
    if not name:
        return jsonify({'error': 'Product name is required'}), 400
    
    products = load_products()
    next_id = get_next_id()
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Add multiple products if quantity > 1
    new_products = []
    for i in range(quantity):
        benefit = calculate_benefit(buy_price, sell_price)
        sell_date = current_date if sell_price > 0 else ''
        product = {
            'id': next_id + i,
            'name': name,
            'serial_number': serial_number,
            'provider': provider,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'benefit': benefit,
            'date': current_date,
            'sell_date': sell_date
        }
        new_products.append(product)
    
    products.extend(new_products)
    save_products(products)
    
    return jsonify({'success': True, 'products_added': len(new_products)})

@app.route('/api/products/update', methods=['POST'])
def update_product():
    """Update existing product"""
    data = request.json
    product_id = int(data.get('id'))
    
    products = load_products()
    for product in products:
        if product['id'] == product_id:
            # Store old sell_price to detect changes
            old_sell_price = product['sell_price']
            
            product['name'] = data.get('name', product['name'])
            product['serial_number'] = data.get('serial_number', product['serial_number'])
            product['provider'] = data.get('provider', product['provider'])
            product['buy_price'] = float(data.get('buy_price', product['buy_price']))
            product['sell_price'] = float(data.get('sell_price', product['sell_price'])) if data.get('sell_price') else 0
            product['benefit'] = calculate_benefit(product['buy_price'], product['sell_price'])
            
            # Set sell_date when sell_price is first added or changed from 0 to a value
            if product['sell_price'] > 0 and old_sell_price == 0:
                product['sell_date'] = datetime.now().strftime('%Y-%m-%d')
            elif product['sell_price'] == 0:
                product['sell_date'] = ''
            
            break
    
    # Auto-save immediately
    save_products(products)
    return jsonify({'success': True})

@app.route('/api/products/delete', methods=['POST'])
def delete_product():
    """Delete a product"""
    data = request.json
    product_id = int(data.get('id'))
    
    products = load_products()
    products = [p for p in products if p['id'] != product_id]
    
    # Auto-save immediately
    save_products(products)
    return jsonify({'success': True})

@app.route('/api/products/save', methods=['POST'])
def save_all_products():
    """Save all products from frontend"""
    data = request.json
    products = data.get('products', [])
    
    # Recalculate benefits for all products
    for product in products:
        product['benefit'] = calculate_benefit(product['buy_price'], product['sell_price'])
    
    save_products(products)
    return jsonify({'success': True})

@app.route('/summary')
def summary():
    """Summary page with analytics"""
    products = load_products()
    return render_template('summary.html', products=products)

@app.route('/api/summary/stats')
def get_summary_stats():
    """Get summary statistics"""
    products = load_products()
    
    # Calculate total benefits (sum of all benefits where sell_price > 0)
    total_benefits = sum(
        float(product.get('benefit', 0)) 
        for product in products 
        if float(product.get('sell_price', 0)) > 0
    )
    
    # Calculate capital (sum of buy_price for unsold products)
    # Unsold = sell_price is 0 or empty
    capital = sum(
        float(product.get('buy_price', 0)) 
        for product in products 
        if float(product.get('sell_price', 0)) == 0
    )
    
    # Additional stats
    total_products = len(products)
    sold_products = len([p for p in products if float(p.get('sell_price', 0)) > 0])
    unsold_products = total_products - sold_products
    
    return jsonify({
        'total_benefits': total_benefits,
        'capital': capital,
        'total_products': total_products,
        'sold_products': sold_products,
        'unsold_products': unsold_products
    })

@app.route('/api/providers')
def get_providers():
    """Get all unique providers"""
    providers = get_unique_providers()
    return jsonify(providers)

if __name__ == '__main__':
    ensure_csv_exists()
    app.run(debug=True, port=5000)

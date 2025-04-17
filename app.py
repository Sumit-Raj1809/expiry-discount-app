import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

app = Flask(__name__)

# Setting up the app configuration from environment variables
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')  # Secure random key for sessions
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///products.db')  # Use env var for DB URL, fallback to SQLite for local

db = SQLAlchemy(app)

# Database model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    expiry = db.Column(db.String(10), nullable=False)

    def discount(self):
        expiry_date = datetime.strptime(self.expiry, '%Y-%m-%d')
        days_left = (expiry_date - datetime.now()).days
        if days_left <= 0:
            return 90
        elif days_left <= 2:
            return 70
        elif days_left <= 5:
            return 50
        elif days_left <= 10:
            return 30
        else:
            return 0

    def final_price(self):
        return round(self.price * (1 - self.discount() / 100), 2)

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def index():
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', '')

    if search_query:
        products_query = Product.query.filter(Product.name.ilike(f'%{search_query}%'))
    else:
        products_query = Product.query

    if sort_by == 'price':
        products_query = products_query.order_by(Product.price)
        products = products_query.all()
    elif sort_by == 'expiry':
        products_query = products_query.order_by(Product.expiry)
        products = products_query.all()
    elif sort_by == 'discount':
        products = sorted(products_query.all(), key=lambda p: p.discount(), reverse=True)
    else:
        products = products_query.all()

    no_results = (len(products) == 0)
    return render_template('index.html', products=products, no_results=no_results)

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        expiry = request.form['expiry']
        new_product = Product(name=name, price=price, expiry=expiry)
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_product.html')

@app.route('/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        product.price = float(request.form['price'])
        product.expiry = request.form['expiry']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('edit.html', product=product)

@app.route('/delete/<int:product_id>')
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('index'))

# ✅ Chart data route
@app.route('/expiry_chart_data')
def expiry_chart_data():
    today = datetime.today().date()
    products = Product.query.all()

    ranges = {'0-3 Days': 0, '4-7 Days': 0, '8-15 Days': 0, '16+ Days': 0}
    for product in products:
        try:
            expiry_date = datetime.strptime(product.expiry, '%Y-%m-%d').date()
            days_left = (expiry_date - today).days
            if days_left <= 3:
                ranges['0-3 Days'] += 1
            elif days_left <= 7:
                ranges['4-7 Days'] += 1
            elif days_left <= 15:
                ranges['8-15 Days'] += 1
            else:
                ranges['16+ Days'] += 1
        except:
            continue  # In case of invalid format

    return jsonify({
        "labels": list(ranges.keys()),
        "counts": list(ranges.values())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)



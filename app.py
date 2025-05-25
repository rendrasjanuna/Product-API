from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
import jwt
import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'rahasia123'

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    products = db.relationship('Product', backref='owner', lazy=True)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token tidak ditemukan!'}), 401

        try:
            token = token.replace('Bearer ', '')
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User tidak ditemukan!'}), 404
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token telah kedaluwarsa!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token tidak valid!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@app.route('/')
def index():
    return 'API User & Product siap'


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username dan Password wajib diisi!'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username sudah terdaftar!'}), 409

    new_user = User(username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Registrasi berhasil!'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username, password=password).first()

    if not user:
        return jsonify({'message': 'Login gagal, cek username/password!'}), 401

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }, app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'message': 'Login berhasil!' , 'token': token})


@app.route('/product', methods=['POST'])
@token_required
def add_product(current_user):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({'message': 'Nama produk wajib diisi!'}), 400

    new_product = Product(name=name, description=description, user_id=current_user.id)
    db.session.add(new_product)
    db.session.commit()

    return jsonify({'message': 'Produk berhasil ditambahkan!'}), 201
    
@app.route('/products', methods=['GET'])
@token_required
def get_all_products(current_user):
    products = Product.query.filter_by(user_id=current_user.id).all()
    output = []
    for p in products:
        output.append({
            'id': p.id,
            'name': p.name,
            'description': p.description
        })

    return jsonify({'products': output})
        

@app.route('/product/<int:id>', methods=['GET'])
@token_required
def get_product(current_user, id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first()
    if not product:
        return jsonify({'message': 'Produk tidak ditemukan!'}), 404

    return jsonify({
        'id': product.id,
        'name': product.name,
        'description': product.description
    })
    
    
         
@app.route('/product/<int:id>', methods=['PUT'])
@token_required
def update_product(current_user, id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first()
    if not product:
        return jsonify({'message': 'Produk tidak ditemukan!'}), 404

    data = request.get_json()
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    db.session.commit()

    return jsonify({
        'message': 'Produk berhasil diupdate!',
        'product': {
            'id': product.id,
            'name': product.name,
            'description': product.description
        }
    })
    
    
@app.route('/product/<int:id>', methods=['DELETE'])
@token_required
def delete_product(current_user, id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first()
    if not product:
        return jsonify({'message': 'Produk tidak ditemukan!'}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({'message': 'Produk berhasil dihapus!'})    


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
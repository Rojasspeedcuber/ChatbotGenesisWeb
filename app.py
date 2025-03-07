import os
import time
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from decouple import config
from functools import wraps
import stripe
from bot.ai_bot import AIBot
from services.db import init_db, db
from services.stripe_service import StripeService
from models.user import User
from models.subscription import Subscription
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = f'{os.urandom(12).hex()}'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
init_db(app)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Get Stripe keys
stripe_public_key = config('STRIPE_PUBLIC_KEY')
stripe_subscription_price_id = config('STRIPE_PRICE_ID')

# Initialize AI bot
ai_bot = AIBot()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def subscription_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))

        if not current_user.has_active_subscription():
            flash('You need an active subscription to access this feature.', 'warning')
            return redirect(url_for('subscription'))

        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        # Create new user
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    has_subscription = current_user.has_active_subscription()
    subscription = Subscription.query.filter_by(
        user_id=current_user.id).first()

    return render_template('dashboard.html',
                           has_subscription=has_subscription,
                           subscription=subscription)


@app.route('/subscription')
@login_required
def subscription():
    has_subscription = current_user.has_active_subscription()
    subscription = Subscription.query.filter_by(
        user_id=current_user.id).first()

    return render_template('subscription.html',
                           stripe_public_key=stripe_public_key,
                           has_subscription=has_subscription,
                           subscription=subscription)


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    # Define success and cancel URLs
    success_url = url_for('subscription_success', _external=True)
    cancel_url = url_for('subscription', _external=True)

    # Create checkout session
    checkout_session = StripeService.create_checkout_session(
        user=current_user,
        price_id=stripe_subscription_price_id,
        success_url=success_url,
        cancel_url=cancel_url
    )

    if checkout_session:
        return redirect(checkout_session.url)

    flash('Failed to create checkout session. Please try again.', 'danger')
    return redirect(url_for('subscription'))


@app.route('/subscription/success')
@login_required
def subscription_success():
    flash('Thank you for subscribing!', 'success')
    return render_template('success.html')


@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({'error': str(e)}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({'error': str(e)}), 400

    # Handle the event
    if StripeService.handle_webhook_event(event):
        return jsonify({'status': 'success'}), 200

    return jsonify({'status': 'unhandled event type'}), 200


@app.route('/chat')
@login_required
@subscription_required
def chat():
    return render_template('chat.html')


@app.route('/api/chat', methods=['POST'])
@login_required
@subscription_required
def api_chat():
    data = request.json
    message = data.get('message', '')
    chat_history = session.get('chat_history', [])

    # Prepare messages for the AI bot
    history_messages = []
    for msg in chat_history:
        # Format messages to match what the bot expects
        if msg['sender'] == 'user':
            history_messages.append({'fromMe': True, 'body': msg['message']})
        else:
            history_messages.append({'fromMe': False, 'body': msg['message']})

    # Get response from AI bot
    response = ai_bot.invoke(
        history_messages=history_messages,
        question=message,
    )

    # Update chat history
    if 'chat_history' not in session:
        session['chat_history'] = []

    session['chat_history'].append(
        {'sender': 'user', 'message': message, 'timestamp': datetime.now().isoformat()})
    session['chat_history'].append(
        {'sender': 'bot', 'message': response, 'timestamp': datetime.now().isoformat()})
    session.modified = True

    return jsonify({'message': response})

# Create admin user if it doesn't exist


@app.before_first_request
def create_admin():
    with app.app_context():
        # Create database tables
        db.create_all()

        # Check if admin user exists
        admin_email = config('ADMIN_EMAIL')
        admin = User.query.filter_by(email=admin_email).first()

        if not admin:
            admin_password = config('ADMIN_PASSWORD', default='adminpassword')
            admin = User(
                username='admin',
                email=admin_email,
                password=admin_password,
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

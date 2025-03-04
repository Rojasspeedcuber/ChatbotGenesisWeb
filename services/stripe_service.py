import stripe
from decouple import config
from models.subscription import Subscription
from services.db import db
from datetime import datetime, timedelta

# Configure Stripe with API key
stripe.api_key = config('STRIPE_SECRET_KEY')


class StripeService:
    @staticmethod
    def create_customer(user):
        """Create a Stripe customer for the user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={"user_id": user.id}
            )
            return customer
        except Exception as e:
            print(f"Error creating Stripe customer: {e}")
            return None

    @staticmethod
    def create_checkout_session(user, price_id, success_url, cancel_url):
        """Create a Stripe checkout session for subscription"""
        try:
            # Check if user already has a Stripe customer ID
            sub = Subscription.query.filter_by(user_id=user.id).first()

            if not sub:
                # Create a new subscription record
                customer = StripeService.create_customer(user)
                sub = Subscription(
                    user_id=user.id,
                    stripe_customer_id=customer.id
                )
                db.session.add(sub)
                db.session.commit()
            elif not sub.stripe_customer_id:
                # Create customer if not exists
                customer = StripeService.create_customer(user)
                sub.stripe_customer_id = customer.id
                db.session.commit()

            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=sub.stripe_customer_id,
                payment_method_types=['card'],
                line_items=[
                    {
                        'price': price_id,
                        'quantity': 1,
                    },
                ],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user.id
                },
            )

            return checkout_session
        except Exception as e:
            print(f"Error creating checkout session: {e}")
            return None

    @staticmethod
    def handle_webhook_event(event):
        """Handle Stripe webhook events"""
        try:
            event_type = event['type']

            if event_type == 'checkout.session.completed':
                session = event['data']['object']
                user_id = int(session.get('metadata', {}).get('user_id', 0))
                customer_id = session.get('customer')
                subscription_id = session.get('subscription')

                if user_id and subscription_id:
                    # Update subscription
                    sub = Subscription.query.filter_by(user_id=user_id).first()
                    if sub:
                        sub.stripe_customer_id = customer_id
                        sub.stripe_subscription_id = subscription_id
                        sub.status = 'active'
                        sub.start_date = datetime.utcnow()
                        sub.end_date = datetime.utcnow() + timedelta(days=30)
                        db.session.commit()

            elif event_type == 'invoice.payment_succeeded':
                invoice = event['data']['object']
                subscription_id = invoice.get('subscription')

                if subscription_id:
                    sub = Subscription.query.filter_by(
                        stripe_subscription_id=subscription_id).first()
                    if sub:
                        # Extend subscription by 30 days
                        if sub.end_date and sub.end_date > datetime.utcnow():
                            sub.end_date = sub.end_date + timedelta(days=30)
                        else:
                            sub.end_date = datetime.utcnow() + timedelta(days=30)
                        sub.status = 'active'
                        db.session.commit()

            elif event_type == 'customer.subscription.deleted':
                subscription_data = event['data']['object']
                subscription_id = subscription_data.get('id')

                if subscription_id:
                    sub = Subscription.query.filter_by(
                        stripe_subscription_id=subscription_id).first()
                    if sub:
                        sub.status = 'canceled'
                        db.session.commit()

            return True
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return False

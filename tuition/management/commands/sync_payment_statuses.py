from django.core.management.base import BaseCommand
from django.conf import settings
from tuition.models import Payment
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

class Command(BaseCommand):
    help = 'Sync payment statuses from Stripe for pending payments'

    def handle(self, *args, **options):
        # Get all pending payments
        pending_payments = Payment.objects.filter(status='pending')
        
        self.stdout.write(f"Found {pending_payments.count()} pending payments")
        
        for payment in pending_payments:
            try:
                # Retrieve the payment intent from Stripe
                payment_intent = stripe.PaymentIntent.retrieve(payment.receipt_number)
                
                if payment_intent.status == 'succeeded':
                    payment.status = 'completed'
                    payment.save()
                    
                    # If this payment doesn't have PaymentItem records yet, create them
                    from django.utils import timezone
                    from decimal import Decimal
                    from tuition.models import PaymentItem, PaymentBreakdown
                    
                    if not PaymentItem.objects.filter(payment=payment).exists():
                        # Get current month's payment items
                        now = timezone.now()
                        current_month = now.month
                        current_year = now.year
                        payment_items = PaymentBreakdown.objects.filter(
                            student=payment.student,
                            is_paid=False,
                            due_date__year=current_year,
                            due_date__month=current_month
                        )
                        
                        # Create PaymentItem records to link payment to breakdown items
                        total_payment_amount = payment.amount
                        payment_items_list = list(payment_items)
                        
                        if payment_items_list:
                            # Calculate how much each item should be paid
                            total_items_amount = sum(item.amount for item in payment_items_list)
                            
                            for item in payment_items_list:
                                if total_items_amount > 0:
                                    # Calculate proportional amount for this item
                                    item_amount = (item.amount / total_items_amount) * total_payment_amount
                                    # Round to 2 decimal places
                                    item_amount = round(item_amount, 2)
                                else:
                                    item_amount = Decimal('0.00')
                                
                                # Create PaymentItem record
                                PaymentItem.objects.create(
                                    payment=payment,
                                    breakdown_item=item,
                                    amount_paid=item_amount,
                                    currency='USD'  # Default to USD
                                )
                            
                            # Mark payment items as paid
                            payment_items.update(is_paid=True)
                            self.stdout.write(
                                self.style.SUCCESS(f"Payment {payment.id} updated to completed and bills marked as paid")
                            )
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(f"Payment {payment.id} updated to completed")
                            )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"Payment {payment.id} updated to completed")
                        )
                elif payment_intent.status == 'failed':
                    payment.status = 'failed'
                    payment.save()
                    self.stdout.write(
                        self.style.ERROR(f"Payment {payment.id} updated to failed")
                    )
                else:
                    self.stdout.write(
                        f"Payment {payment.id} still {payment_intent.status}"
                    )
                    
            except stripe.error.StripeError as e:
                self.stdout.write(
                    self.style.ERROR(f"Error checking payment {payment.id}: {str(e)}")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Unexpected error for payment {payment.id}: {str(e)}")
                )
        
        self.stdout.write(self.style.SUCCESS("Payment status sync completed")) 
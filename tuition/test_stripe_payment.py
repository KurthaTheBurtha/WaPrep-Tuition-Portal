# """
# PCI-compliant Stripe unit-test flow
# ----------------------------------
# * Uses predefined test PaymentMethod (`pm_card_visa`) – no raw PAN touches the server.
# * Demonstrates attaching to a Customer and creating / retrieving a PaymentIntent.
# * Suitable for unit tests; swap to Elements or Checkout for your production flow.
# """
# import os
# import stripe
# from dotenv import load_dotenv
# import logging

# # ---------- 0.  Setup ----------
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# load_dotenv()
# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# def _mask(key: str) -> str:
#     """Utility: mask secret key in logs."""
#     return f"{key[:8]}…{key[-4:]}" if key else "NOT-SET"

# logger.debug(f"Using Stripe key: {_mask(stripe.api_key)}")

# # ---------- 1.  Customer ----------
# def test_create_customer() -> stripe.Customer:
#     customer = stripe.Customer.create(
#         email="test@example.com",
#         name="Test Customer",
#         metadata={"student_id": "123", "payer_id": "456"},
#     )
#     logger.info("Created customer %s", customer.id)
#     return customer

# # ---------- 2.  PaymentMethod ----------
# def test_get_test_payment_method() -> stripe.PaymentMethod:
#     """
#     In test mode you can *retrieve* a predefined PaymentMethod rather than creating
#     one from raw card data. pm_card_visa always exists in every test account.  See docs. :contentReference[oaicite:1]{index=1}
#     """
#     pm = stripe.PaymentMethod.retrieve("pm_card_visa")
#     logger.info("Using PaymentMethod %s", pm.id)
#     return pm

# # ---------- 3.  Attach ----------
# def test_attach_payment_method(cust_id: str, pm_id: str) -> None:
#     stripe.PaymentMethod.attach(pm_id, customer=cust_id)
#     # Optionally set as default:
#     stripe.Customer.modify(cust_id, invoice_settings={"default_payment_method": pm_id})
#     logger.info("Attached %s to customer %s", pm_id, cust_id)

# # ---------- 4.  PaymentIntent ----------
# def test_create_payment_intent(cust_id: str, pm_id: str, amount_cents: int
# ) -> stripe.PaymentIntent:
#     """
#     For unit tests we can confirm immediately because we’re using a
#     *test* PaymentMethod ID. In production, create the intent and let the
#     client confirm via Stripe.js.
#     """
#     intent = stripe.PaymentIntent.create(
#         amount=amount_cents,
#         currency="usd",
#         customer=cust_id,
#         payment_method=pm_id,
#         confirm=True,            # Safe only with predefined test PMs
#         off_session=True,
#         metadata={
#             "student_id": "123",
#             "payer_id": "456",
#             "payment_type": "tuition",
#         },
#     )
#     logger.info("Created & confirmed PI %s – status=%s", intent.id, intent.status)
#     return intent

# # ---------- 5.  Retrieve ----------
# def test_retrieve_payment_intent(pi_id: str) -> stripe.PaymentIntent:
#     intent = stripe.PaymentIntent.retrieve(pi_id)
#     logger.info("Retrieved PI %s – status=%s", intent.id, intent.status)
#     return intent

# # ---------- 6.  Main test run ----------
# def main() -> None:
#     customer = test_create_customer()
#     pm = test_get_test_payment_method()
#     test_attach_payment_method(customer.id, pm.id)
#     intent = test_create_payment_intent(customer.id, pm.id, amount_cents=10_000)
#     test_retrieve_payment_intent(intent.id)
#     logger.info("🎉  All tests passed")

# if __name__ == "__main__":
#     main()

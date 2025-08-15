# Bank Account Payment Testing Guide

## The Challenge

When testing bank account payments with Stripe, you encounter an extra authentication step (microdeposits verification) that cannot be automated in test mode. This is a security requirement from Stripe.

## Solutions for Testing

### Option 1: Test Through Your Web Interface (Recommended)

The best way to test bank account payments is through your actual web interface:

1. **Start your Django server:**
   ```bash
   python manage.py runserver
   ```

2. **Create a test student and payment items:**
   - Go to your admin interface
   - Create a test student
   - Add some payment breakdown items

3. **Test the payment flow:**
   - Login as a payer
   - Navigate to the payment page
   - Use Stripe's test bank account numbers:
     - **Routing Number:** `110000000`
     - **Account Number:** `000123456789`
     - **Account Type:** Checking

4. **Handle the verification step:**
   - When prompted for microdeposits verification, click the verification URL
   - Enter the test amounts: **32 cents** and **45 cents**
   - Complete the verification

### Option 2: Use Credit Cards for Testing

Credit card payments work immediately without verification:

1. **Test with Stripe's test cards:**
   - **Success:** `4242424242424242`
   - **Decline:** `4000000000000002`
   - **Expiry:** Any future date
   - **CVC:** Any 3 digits

2. **This allows you to test:**
   - Payment processing flow
   - Database updates
   - Receipt generation
   - Error handling

### Option 3: Mock the Bank Account Verification

For automated testing, you can mock the verification step:

```python
# In your test code, simulate a verified bank account
def mock_bank_account_verification():
    # Create a PaymentMethod that appears verified
    payment_method = stripe.PaymentMethod.create(
        type='us_bank_account',
        us_bank_account={
            'routing_number': '110000000',
            'account_number': '000123456789',
            'account_holder_type': 'individual',
            'account_type': 'checking'
        }
    )
    
    # In test mode, you can simulate the verification
    # by directly updating your database
    return payment_method
```

## Stripe Test Bank Account Numbers

Use these official Stripe test numbers:

| Account Number | Type | Status |
|----------------|------|--------|
| `000123456789` | Checking | Requires verification |
| `000111111116` | Savings | Requires verification |
| `000222222227` | Checking | Requires verification |

## Test Microdeposit Amounts

When verification is required, use these test amounts:
- **First deposit:** 32 cents ($0.32)
- **Second deposit:** 45 cents ($0.45)

## Production Considerations

### For Real Users

1. **Bank Account Verification:**
   - Users must verify their bank accounts
   - Stripe sends microdeposits (usually 32¢ and 45¢)
   - Users enter these amounts to verify ownership
   - This is a one-time process per bank account

2. **Verification Flow:**
   ```
   User adds bank account → Stripe sends microdeposits → 
   User enters amounts → Account verified → Can make payments
   ```

3. **User Experience:**
   - Clear instructions about the verification process
   - Explain that microdeposits will appear in 1-2 business days
   - Provide support for users who don't receive deposits

### Security Best Practices

1. **Never store full account numbers**
2. **Use Stripe's hosted verification pages**
3. **Implement proper error handling**
4. **Log payment attempts for debugging**

## Testing Checklist

- [ ] Test credit card payments (immediate success)
- [ ] Test bank account addition flow
- [ ] Test microdeposits verification process
- [ ] Test payment success scenarios
- [ ] Test payment failure scenarios
- [ ] Test database record creation
- [ ] Test receipt generation
- [ ] Test error handling

## Common Issues and Solutions

### Issue: "PaymentIntent requires a mandate"
**Solution:** Bank account payments require mandate acceptance. Use the web interface where Stripe handles this automatically.

### Issue: "PaymentMethod must be verified"
**Solution:** This is expected for bank accounts. Complete the microdeposits verification or use credit cards for testing.

### Issue: "Raw card data APIs not enabled"
**Solution:** Use Stripe Elements in the web interface instead of direct API calls for card numbers.

## Recommended Testing Approach

1. **Start with credit cards** - Test the full payment flow
2. **Test bank account addition** - Verify the UI works
3. **Test microdeposits verification** - Complete the full bank account flow once
4. **Automate with mocks** - For continuous integration testing

## Next Steps

1. Run your Django server and test through the web interface
2. Use the test bank account numbers provided
3. Complete the microdeposits verification manually
4. Verify that payments are recorded correctly in your database

This approach will give you confidence that your bank account payment system works correctly while respecting Stripe's security requirements. 
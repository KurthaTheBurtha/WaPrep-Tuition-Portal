# 📊 Billing & Payment Monitoring Commands Guide

This guide provides all the commands and examples for monitoring your tuition system's billing and payment changes.

## 🎯 Quick Start

### Basic Summary (Last 7 Days)
```bash
python manage.py monitor_billing_changes --action summary
```

### All Changes (Last 7 Days)
```bash
python manage.py monitor_billing_changes --action detailed
```

---

## 📋 Available Commands

### 1. **Summary Overview** (`--action summary`)
Shows overall statistics and financial summaries.

```bash
python manage.py monitor_billing_changes --action summary --days 7
```

**What it shows:**
- Total bill changes (CREATE, UPDATE, DELETE)
- Total payment changes
- Total payment allocations
- Financial summary (total payments, amounts, averages)

**Example Output:**
```
💰 Billing & Payment Change Monitor - Last 7 days
======================================================================

📊 BILLING & PAYMENT SUMMARY
----------------------------------------
📝 Bill Changes: 15
   CREATE: 8
   UPDATE: 6
   DELETE: 1

💳 Payment Changes: 12
   CREATE: 12
   UPDATE: 8

🔗 Payment Allocations: 24

💰 Financial Summary:
   Total Payments: 12
   Total Amount: $6,500.00
   Average Payment: $541.67
```

### 2. **Bill Changes Only** (`--action bills`)
Shows detailed bill creation, updates, and deletions.

```bash
python manage.py monitor_billing_changes --action bills --days 7
```

**What it shows:**
- Bill creation details
- Field changes (amount, due date, description, status)
- Student information
- User who made the change
- Timestamps

**Example Output:**
```
📋 BILL CHANGES DETAIL
----------------------------------------

🕒 2025-07-21 14:30
   Action: CREATE
   Student: John Smith
   Bill: March Tuition
   Amount: $500.00
   User: admin_user
   Description: New tuition bill for March 2025

🕒 2025-07-21 14:35
   Action: UPDATE
   Student: John Smith
   Bill: March Tuition
   Amount: $500.00
   User: admin_user
   Field: is_paid
   Old: False
   New: True
   Description: Bill marked as paid
```

### 3. **Payment Changes Only** (`--action payments`)
Shows detailed payment creation and status changes.

```bash
python manage.py monitor_billing_changes --action payments --days 7
```

**What it shows:**
- Payment creation details
- Status changes (pending → completed → failed)
- Payment method changes
- Amount modifications
- Student and payer information

**Example Output:**
```
💳 PAYMENT CHANGES DETAIL
----------------------------------------

🕒 2025-07-21 15:00
   Action: CREATE
   Student: John Smith
   Amount: $300.00
   Status: pending
   Method: credit_card
   User: john_doe

🕒 2025-07-21 15:02
   Action: UPDATE
   Student: John Smith
   Amount: $300.00
   Status: completed
   Method: credit_card
   User: system
   Field: status
   Old: pending
   New: completed
   Description: Payment processed successfully
```

### 4. **Payment Allocations Only** (`--action allocations`)
Shows how payments are allocated to specific bills.

```bash
python manage.py monitor_billing_changes --action allocations --days 7
```

**What it shows:**
- Payment allocation details
- Which bills received payment
- Amount allocated to each bill
- Payment status and method

**Example Output:**
```
🔗 PAYMENT ALLOCATIONS DETAIL
----------------------------------------

🕒 2025-07-21 15:05
   Action: CREATE
   Student: John Smith
   Payment: $300.00 (completed)
   Bill: March Tuition
   Allocated: $300.00
   User: system
   Description: Payment allocated to tuition bill
```

### 5. **All Changes Chronologically** (`--action detailed`)
Shows all billing and payment changes in chronological order.

```bash
python manage.py monitor_billing_changes --action detailed --days 7
```

**What it shows:**
- All changes in time order
- Mixed bill, payment, and allocation events
- Complete audit trail

**Example Output:**
```
📋 ALL CHANGES CHRONOLOGICAL
----------------------------------------

🕒 2025-07-21 14:30:00
   CREATE | PaymentBreakdown | John Smith
   User: admin_user

🕒 2025-07-21 15:00:00
   CREATE | Payment | John Smith
   User: john_doe

🕒 2025-07-21 15:02:00
   UPDATE | Payment | John Smith
   User: system
   Field: status | pending → completed

🕒 2025-07-21 15:05:00
   CREATE | PaymentItem | John Smith
   User: system
   Description: Payment allocated to tuition bill
```

---

## 🔍 Filtering Options

### Filter by Time Period
```bash
# Last 1 day
python manage.py monitor_billing_changes --action summary --days 1

# Last 30 days
python manage.py monitor_billing_changes --action summary --days 30

# Last 90 days
python manage.py monitor_billing_changes --action summary --days 90
```

### Filter by Student
```bash
# All changes for a specific student
python manage.py monitor_billing_changes --action detailed --student "John Smith"

# Partial name matching
python manage.py monitor_billing_changes --action detailed --student "John"

# Multiple students with same first name
python manage.py monitor_billing_changes --action detailed --student "Sarah"
```

### Filter by User (Who Made Changes)
```bash
# All changes made by a specific user
python manage.py monitor_billing_changes --action detailed --user "admin_user"

# All changes made by admin users
python manage.py monitor_billing_changes --action detailed --user "admin"

# All changes made by a specific payer
python manage.py monitor_billing_changes --action detailed --user "john_doe"
```

### Combined Filters
```bash
# Specific student, specific user, last 30 days
python manage.py monitor_billing_changes --action detailed --student "John Smith" --user "admin_user" --days 30

# All admin changes for students with "Smith" in name, last 7 days
python manage.py monitor_billing_changes --action detailed --student "Smith" --user "admin" --days 7
```

---

## 📊 Common Monitoring Scenarios

### 1. **Daily Summary Check**
```bash
python manage.py monitor_billing_changes --action summary --days 1
```
**Use case:** Quick daily overview of all billing activity

### 2. **Weekly Financial Review**
```bash
python manage.py monitor_billing_changes --action summary --days 7
```
**Use case:** Weekly financial reporting and analysis

### 3. **Student Account Audit**
```bash
python manage.py monitor_billing_changes --action detailed --student "John Smith" --days 30
```
**Use case:** Complete audit trail for a specific student

### 4. **Admin Activity Monitoring**
```bash
python manage.py monitor_billing_changes --action detailed --user "admin" --days 7
```
**Use case:** Monitor all changes made by administrators

### 5. **Payment Processing Review**
```bash
python manage.py monitor_billing_changes --action payments --days 7
```
**Use case:** Review all payment processing and status changes

### 6. **Bill Creation Tracking**
```bash
python manage.py monitor_billing_changes --action bills --days 7
```
**Use case:** Monitor new bill creation and modifications

### 7. **Payment Allocation Verification**
```bash
python manage.py monitor_billing_changes --action allocations --days 7
```
**Use case:** Verify how payments are being allocated to bills

---

## 🛠️ Additional Monitoring Tools

### General System Monitoring
```bash
# Overall system activity
python manage.py logging_monitor --action summary --days 7

# User activity analysis
python manage.py logging_monitor --action users --days 7

# Security events
python manage.py logging_monitor --action security --days 7

# System health
python manage.py logging_monitor --action health --days 7
```

### Test the Logging System
```bash
# Basic logging test
python manage.py test_logging

# Full test with data modifications
python manage.py test_logging --full
```

---

## 📈 Understanding the Output

### Action Types
- **CREATE**: New record created
- **UPDATE**: Existing record modified
- **DELETE**: Record deleted

### Model Names
- **PaymentBreakdown**: Bills/invoices
- **Payment**: Payment transactions
- **PaymentItem**: Payment allocations to bills
- **Student**: Student information changes

### Field Changes
When a field is modified, you'll see:
- **Field**: Name of the changed field
- **Old**: Previous value
- **New**: New value

### User Information
- **admin_user**: System administrator
- **system**: Automated system processes
- **john_doe**: Regular user/payer

---

## 🔧 Troubleshooting

### No Results Found
If you get no results, try:
1. **Increase the time period**: `--days 30` instead of `--days 1`
2. **Remove filters**: Don't use `--student` or `--user` filters
3. **Check for activity**: Use the general logging monitor first

### Command Not Found
If the command isn't recognized:
1. **Check Django setup**: Ensure you're in the correct directory
2. **Run migrations**: `python manage.py makemigrations && python manage.py migrate`
3. **Check file permissions**: Ensure the command file exists

### Permission Issues
If you get permission errors:
1. **Check file permissions**: Ensure the command file is executable
2. **Use correct Python environment**: Activate your virtual environment
3. **Check Django settings**: Ensure settings are properly configured

---

## 📞 Support

If you encounter issues:
1. **Check the logs**: Look at `logs/audit.log` for detailed information
2. **Test the system**: Run `python manage.py test_logging` to verify functionality
3. **Review Django admin**: Check the Audit Logs section in Django admin

---

## 🎯 Quick Reference Card

| Command | Purpose | Example |
|---------|---------|---------|
| `--action summary` | Overview statistics | `--action summary --days 7` |
| `--action bills` | Bill changes only | `--action bills --days 7` |
| `--action payments` | Payment changes only | `--action payments --days 7` |
| `--action allocations` | Payment allocations only | `--action allocations --days 7` |
| `--action detailed` | All changes chronologically | `--action detailed --days 7` |
| `--student "Name"` | Filter by student | `--student "John Smith"` |
| `--user "username"` | Filter by user | `--user "admin_user"` |
| `--days N` | Time period in days | `--days 30` |

**Most Common Commands:**
```bash
# Daily summary
python manage.py monitor_billing_changes --action summary --days 1

# Weekly detailed review
python manage.py monitor_billing_changes --action detailed --days 7

# Student audit
python manage.py monitor_billing_changes --action detailed --student "Student Name" --days 30
``` 
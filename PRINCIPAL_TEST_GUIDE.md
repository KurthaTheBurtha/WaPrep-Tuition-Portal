# WaPrep Tuition Portal - Principal Test Guide

## Quick Start Testing Plan

This guide provides a systematic approach for the principal to test the tuition portal efficiently. Follow these steps in order for comprehensive testing.

How To Use:
    - Print it out or have it open on a second screen
    - Follow phases in order - don't skip around
    - Document issues immediately using the template (bottom)
    - Take screenshots of any problems
    - Complete each phase before moving to the next
    - Use the quick reference for common tasks (bottom)
---

## Phase 1: Initial Setup & Basic Functionality (30 minutes)

### 1.1 Environment Setup
**Actions:**
1. Open the application in Chrome browser
2. Clear browser cache and cookies
3. Have a notepad ready to document any issues

### 1.2 Home Page & Navigation
**Actions:**
1. **Test Home Page**: Visit the main page
   - Verify the page loads completely
   - Check that both "Admin Login" and "Payer Login" options are visible
   - Confirm the WaPrep logo and branding are displayed correctly

2. **Test Navigation**: Click each login option
   - Click "Admin Login" - should take you to admin login page
   - Click "Payer Login" - should take you to payer login page
   - Use browser back button to return to home page

### 1.3 Basic Login Testing
**Actions:**
1. **Test Invalid Logins** (Security Check):
   - Go to Admin Login page
   - Try logging in with fake credentials (email: test@test.com, password: wrong)
   - Verify you get an error message
   - Try leaving fields empty and submitting
   - Verify required field validation works

2. **Test Payer Login Page**:
   - Go to Payer Login page
   - Try logging in with fake credentials
   - Verify error messages appear

---

## Phase 2: Admin Functionality Testing (45 minutes)

### 2.1 Admin Login & Dashboard
**Actions:**
1. **Login as Admin**:
   - Use your admin credentials to log in
   - Verify you're redirected to the admin dashboard
   - Check that the dashboard loads completely

2. **Test Admin Dashboard**:
   - Verify all navigation links work (Students, Admin Dashboard, etc.)
   - Check that student statistics are displayed
   - Verify the logout button works

### 2.2 Student Management
**Actions:**
1. **View Students List**:
   - Click on "Students" in navigation
   - Verify the students list loads
   - Check that student information is displayed correctly

2. **Add a Test Student**:
   - Click "Add Student" button
   - Fill out the form with test data:
     - First Name: Test
     - Last Name: Student
     - Date of Birth: 01/01/2010
     - Grade: 5th Grade
   - Submit the form
   - Verify the student appears in the list
   - Note the generated Student ID

3. **Edit Student Information**:
   - Click on the test student you just created
   - Try editing some information (like notes)
   - Save changes
   - Verify changes are saved

4. **Test Student Status**:
   - Change the student status from Active to Inactive
   - Verify the change is saved
   - Change it back to Active

### 2.3 User Management
**Actions:**
1. **Create a Test Payer Account**:
   - Go to student management
   - Find a student and click "Add Payer"
   - Fill out payer information:
     - First Name: Test
     - Last Name: Payer
     - Email: testpayer@example.com
     - Relationship: Mother
   - Submit the form
   - Verify the payer is associated with the student

2. **Test Payer Activation**:
   - Check that the payer account needs activation
   - Send activation email (if this feature is available)
   - Note the temporary password or activation link

---

## Phase 3: Payer Functionality Testing (30 minutes)

### 3.1 Payer Login & Dashboard
**Actions:**
1. **Login as Payer**:
   - Use the test payer account you just created
   - If activation is required, follow the activation process
   - Verify you're logged in as a payer

2. **Test Payer Dashboard**:
   - Check that you can see the associated student(s)
   - Verify the dashboard shows current balance
   - Test all navigation links

### 3.2 Payment Method Setup
**Actions:**
1. **Add Payment Method**:
   - Go to "Manage Payment Methods"
   - Try adding a bank account (use test data)
   - Try adding a credit card (use test data)
   - Verify payment methods are saved

2. **Test Payment Method Management**:
   - Edit payment method nicknames
   - Remove a payment method
   - Verify changes are saved

### 3.3 Profile Management
**Actions:**
1. **Edit Payer Profile**:
   - Go to "Payer Profile"
   - Edit your name or email
   - Save changes
   - Verify changes are reflected

---

## Phase 4: Billing & Payment Testing (45 minutes)

### 4.1 Bill Creation (Admin)
**Actions:**
1. **Create Test Bills**:
   - Login as admin
   - Go to "Manage Billing"
   - Select a student
   - Add a test bill:
     - Description: Test Tuition
     - Amount: $100.00
     - Due Date: Next month
   - Submit the bill
   - Verify the bill appears in the student's billing

2. **Test Bill Management**:
   - Edit the bill amount or due date
   - Mark the bill as paid
   - Verify status changes

### 4.2 Payment Processing (Payer)
**Actions:**
1. **Make a Test Payment**:
   - Login as payer
   - Go to payment section
   - Select the test bill you created
   - Enter payment amount ($50.00)
   - Select a payment method
   - Submit payment
   - Verify payment confirmation

2. **Test Payment History**:
   - Go to payment history
   - Verify your test payment appears
   - Check payment details
   - Download receipt (if available)

### 4.3 Payment Allocation
**Actions:**
1. **Test Partial Payments**:
   - Create another test bill for $200
   - Make a partial payment of $75
   - Verify the remaining balance is correct
   - Check that payment is allocated properly

---

## Phase 5: Advanced Features Testing (30 minutes)

### 5.1 Reporting & Analytics
**Actions:**
1. **Test Admin Reports**:
   - Login as admin
   - Go to "Admin Reports" or "Dashboard"
   - Check payment summaries
   - Verify student statistics
   - Test any export functions

2. **Test Audit Logs**:
   - Check if audit logs are accessible
   - Verify that your test actions are logged
   - Test audit report generation

### 5.2 Security Features
**Actions:**
1. **Test Session Security**:
   - Login as admin
   - Leave the browser idle for 10-15 minutes
   - Try to perform an action
   - Verify you're logged out automatically

2. **Test Authorization**:
   - Login as payer
   - Try to access admin URLs directly
   - Verify you're blocked from admin functions

3. **Test Password Security**:
   - Try to change password to a weak password
   - Verify password strength requirements
   - Test password reset functionality

### 5.3 Error Handling
**Actions:**
1. **Test Invalid Inputs**:
   - Try entering invalid email formats
   - Try entering negative payment amounts
   - Try entering future birth dates
   - Verify appropriate error messages appear

2. **Test Network Issues**:
   - Disconnect internet briefly during an action
   - Reconnect and verify the system handles it gracefully

---

## Phase 6: Mobile & Browser Testing (20 minutes)

### 6.1 Mobile Testing
**Actions:**
1. **Test Mobile Responsiveness**:
   - Open the app on your phone
   - Test login functionality
   - Check that all buttons are touch-friendly
   - Verify text is readable on small screens

2. **Test Mobile Navigation**:
   - Navigate through different sections
   - Test form inputs on mobile
   - Verify payment process works on mobile

### 6.2 Cross-Browser Testing
**Actions:**
1. **Test Different Browsers**:
   - Open the app in Firefox
   - Test basic login and navigation
   - Open the app in Safari (if available)
   - Test basic functionality
   - Note any differences in appearance or behavior

---

## Phase 7: Performance & Load Testing (15 minutes)

### 7.1 Performance Testing
**Actions:**
1. **Test Page Load Times**:
   - Use browser developer tools (F12)
   - Go to Network tab
   - Load different pages and note load times
   - Verify pages load in under 3 seconds

2. **Test with Multiple Students**:
   - Create 5-10 test students
   - Verify the students list still loads quickly
   - Test searching and filtering

### 7.2 System Health
**Actions:**
1. **Check System Health**:
   - Look for any health check or monitoring pages
   - Verify system status indicators
   - Check for any error logs or warnings

---

## Phase 8: Final Validation & Cleanup (15 minutes)

### 8.1 Data Validation
**Actions:**
1. **Verify Data Integrity**:
   - Check that all test data is consistent
   - Verify payment calculations are correct
   - Confirm student balances are accurate

2. **Test Data Export**:
   - Try exporting student lists
   - Try exporting payment reports
   - Verify exported data is accurate

### 8.2 Cleanup
**Actions:**
1. **Remove Test Data**:
   - Delete test students you created
   - Remove test payment methods
   - Clean up any test bills
   - Verify cleanup is complete

### 8.3 Final Walkthrough
**Actions:**
1. **Complete System Walkthrough**:
   - Login as admin one final time
   - Verify all main functions work
   - Login as payer one final time
   - Verify payer functions work
   - Test logout functionality

---

## Issue Documentation Template

For each issue you find, document:

**Issue #**: [Number]
**Date**: [Date found]
**Time**: [Time found]
**Page/Function**: [Where the issue occurred]
**Steps to Reproduce**: [Step-by-step instructions]
**Expected Result**: [What should happen]
**Actual Result**: [What actually happened]
**Severity**: [Critical/High/Medium/Low]
**Browser/Device**: [What you were using]
**Screenshots**: [If applicable]

---

## Quick Reference Commands

### Test Data Creation
- **Admin Login**: [Your admin credentials]
- **Test Student**: Test Student (01/01/2010, 5th Grade)
- **Test Payer**: Test Payer (testpayer@example.com)
- **Test Bill**: $100 tuition bill
- **Test Payment**: $50 partial payment

### Key URLs to Test
- Home: `/`
- Admin Login: `/login/admin/`
- Payer Login: `/login/payer/`
- Students: `/students/`
- Admin Dashboard: `/admin/dashboard/`
- Payer Dashboard: `/payer/dashboard/`
- Payment History: `/payment/history/`
- Manage Billing: `/manage-billing/`

### Critical Functions to Verify
- [ ] User authentication works
- [ ] Student creation and management
- [ ] Payer account creation and activation
- [ ] Bill creation and management
- [ ] Payment processing
- [ ] Payment allocation
- [ ] Reporting and analytics
- [ ] Security and authorization
- [ ] Mobile responsiveness
- [ ] Error handling

---

## Testing Tips

1. **Take Notes**: Document everything as you go
2. **Take Screenshots**: Capture any issues or unexpected behavior
3. **Test One Thing at a Time**: Don't rush through multiple functions
4. **Verify Results**: Always confirm that actions produce expected results
5. **Test Edge Cases**: Try unusual inputs or scenarios
6. **Check Error Messages**: Verify error messages are helpful and clear
7. **Test Workflows**: Complete full user journeys from start to finish

---

## Success Criteria

The application is ready for production if:
- [ ] All login functions work correctly
- [ ] Student management is fully functional
- [ ] Payment processing works end-to-end
- [ ] Security measures are effective
- [ ] Mobile experience is satisfactory
- [ ] Performance is acceptable
- [ ] Error handling is robust
- [ ] No critical bugs are found

**Total Estimated Testing Time: 3-4 hours**

*This guide provides a comprehensive yet efficient approach to testing the WaPrep Tuition Portal. Follow the phases in order for best results.* 
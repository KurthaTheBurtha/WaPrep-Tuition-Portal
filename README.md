# WaPrep Tuition Portal

A comprehensive Django-based web application for managing tuition classes, student information, payments, and billing with advanced monitoring and audit capabilities.

## 🚀 Features

### Core Functionality
- **User Authentication & Authorization**: Secure login system with role-based access (Admin/Payer)
- **Student Management**: Complete student profiles with status tracking and balance management
- **Payment Processing**: Integrated payment system with multiple payment methods
- **Billing System**: Automated billing with due dates, late fees, and payment tracking
- **Account Management**: Bank account and card management for recurring payments

### Advanced Features
- **Comprehensive Audit System**: Complete change tracking and data versioning
- **Real-time Monitoring**: System health checks and performance monitoring
- **Security Monitoring**: Detection and logging of security events
- **Payment Allocations**: Automatic allocation of payments to specific bills
- **Receipt Generation**: Automated receipt creation and management
- **Password Security**: Password history tracking and secure reset functionality

### Administrative Tools
- **Dashboard Analytics**: Financial summaries and student statistics
- **Bulk Operations**: Mass updates and data management
- **Reporting System**: Comprehensive audit reports and compliance documentation
- **Backup & Recovery**: Automated backup system with cloud storage integration

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Git
- PostgreSQL (recommended for production)
- Redis (optional, for caching)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone https://github.com/KurthaTheBurtha/WaPrep-Tuition-Portal.git
cd WaPrep-Tuition-Portal
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
Create a `.env` file based on `env.example`:
```bash
cp env.example .env
```

Configure your environment variables:
```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/waprep_tuition

# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe (for payments)
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# AWS S3 (for file storage and backups)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-west-2
```

### 5. Database Setup
```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Start Development Server
```bash
python manage.py runserver
```

The application will be available at `http://127.0.0.1:8000/`

## 📁 Project Structure

```
waprep_tuition/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── runtime.txt              # Python version specification
├── Procfile                 # Deployment configuration
├── build.sh                 # Build script
├── check_email.py           # Email verification utility
├── logs/                    # Application logs
├── scripts/                 # Utility scripts
│   ├── daily_backup.sh      # Automated backup script
│   └── recovery.py          # Recovery utilities
├── static/                  # Static files
├── tuition/                 # Main application
│   ├── migrations/          # Database migrations
│   ├── management/          # Custom management commands
│   │   └── commands/        # Django management commands
│   ├── static/              # App-specific static files
│   ├── templates/           # HTML templates
│   ├── __init__.py
│   ├── admin.py            # Django admin configuration
│   ├── apps.py             # App configuration
│   ├── audit_middleware.py # Audit and security middleware
│   ├── bill_api.py         # Billing API endpoints
│   ├── decorators.py       # Custom decorators
│   ├── forms.py            # Django forms
│   ├── logging_filters.py  # Logging configuration
│   ├── models.py           # Database models
│   ├── settings.py         # Django settings
│   ├── settings_production.py  # Production settings
│   ├── settings_staging.py     # Staging settings
│   ├── tests.py            # Test cases
│   ├── urls.py             # URL routing
│   ├── utils.py            # Utility functions
│   ├── views.py            # View functions
│   └── wsgi.py             # WSGI configuration
└── venv/                   # Virtual environment
```

## 🔧 Management Commands

### System Monitoring
```bash
# Monitor billing and payment changes
python manage.py monitor_billing_changes --action summary --days 7

# Generate audit reports
python manage.py audit_report --days 30

# System health check
python manage.py system_monitor

# Clean up old logs
python manage.py cleanup_logs --days 90
```

### Data Management
```bash
# Create test data
python manage.py create_dummy_payments
python manage.py create_schimmel_test_bills

# Add future bills
python manage.py add_future_bills

# Sync payment statuses
python manage.py sync_payment_statuses
```

### User Management
```bash
# Create admin user
python manage.py create_admin

# Create payer account
python manage.py create_payer

# Create superuser
python manage.py create_superuser
```

## 📊 Monitoring & Logging

The system includes comprehensive monitoring capabilities:

### Audit System
- **Change Tracking**: All data modifications are automatically logged
- **Version Control**: Complete data versioning for critical records
- **User Activity**: Track all user actions and system access
- **Security Events**: Monitor for suspicious activity and security threats

### Monitoring Commands
```bash
# Quick summary of recent activity
python manage.py monitor_billing_changes --action summary --days 1

# Detailed audit trail
python manage.py monitor_billing_changes --action detailed --days 7

# Student-specific audit
python manage.py monitor_billing_changes --student "John Smith" --days 30

# Payment processing review
python manage.py monitor_billing_changes --action payments --days 7
```

For detailed monitoring information, see [MONITORING_COMMANDS_GUIDE.md](MONITORING_COMMANDS_GUIDE.md) and [MONITORING_GUIDE.md](MONITORING_GUIDE.md).

## 🚀 Deployment

### Production Deployment
The application is configured for deployment on various platforms:

- **Railway**: Configured with `Procfile` and `runtime.txt`
- **Render**: Compatible with Render's Django deployment
- **Heroku**: Ready for Heroku deployment
- **AWS**: Configured for AWS deployment

### Backup & Recovery
The system includes automated backup and recovery:

```bash
# Manual backup
python scripts/daily_backup.sh

# Automated daily backups (configured via cron)
0 2 * * * /path/to/scripts/daily_backup.sh
```

For detailed deployment instructions, see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## 🔒 Security Features

- **Password Security**: Password history tracking and secure reset
- **Audit Logging**: Complete audit trail for compliance
- **Security Monitoring**: Real-time security event detection
- **Data Encryption**: Sensitive data encryption and secure storage
- **Access Control**: Role-based access control and permissions

## 📈 Key Models

### Core Models
- **Student**: Student information and status management
- **User**: User accounts with role-based permissions
- **Payment**: Payment transactions and processing
- **PaymentBreakdown**: Billing items and invoices
- **PaymentItem**: Payment allocations to specific bills

### Audit Models
- **AuditLog**: Comprehensive change tracking
- **DataVersion**: Data versioning and snapshots
- **SystemHealth**: System performance monitoring
- **SecurityEvent**: Security incident tracking

## 🧪 Testing

```bash
# Run all tests
python manage.py test

# Run specific test
python manage.py test tuition.tests

# Test logging system
python manage.py test_logging
```

## 📚 Documentation

- [MONITORING_COMMANDS_GUIDE.md](MONITORING_COMMANDS_GUIDE.md) - Monitoring and audit commands
- [MONITORING_GUIDE.md](MONITORING_GUIDE.md) - System monitoring architecture
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment and backup procedures
- [BANK_ACCOUNT_TESTING_GUIDE.md](tuition/BANK_ACCOUNT_TESTING_GUIDE.md) - Bank account testing procedures

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`python manage.py test`)
6. Commit your changes (`git commit -am 'Add some feature'`)
7. Push to the branch (`git push origin feature/your-feature`)
8. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support and questions:
- Open an issue in the GitHub repository
- Check the documentation in the `/docs` folder
- Review the monitoring guides for system troubleshooting

## 🔄 Version History

- **v2.0**: Added comprehensive audit system and monitoring
- **v1.5**: Enhanced payment processing and billing features
- **v1.0**: Initial release with basic tuition management

---

**Note**: This is a production-ready application with comprehensive monitoring, audit capabilities, and security features. Ensure proper configuration of environment variables and database setup before deployment. 
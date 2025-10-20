#!/usr/bin/env python
"""
Script to toggle the download spreadsheet functionality on/off
"""
import os
import sys
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def toggle_spreadsheet_download(enable=True):
    """Toggle the download spreadsheet functionality"""
    
    # File paths
    template_file = BASE_DIR / "tuition" / "templates" / "manage_billing.html"
    urls_file = BASE_DIR / "tuition" / "urls.py"
    views_file = BASE_DIR / "tuition" / "views.py"
    
    if enable:
        print("Enabling download spreadsheet functionality...")
        
        # Enable in template
        with open(template_file, 'r') as f:
            content = f.read()
        
        # Uncomment the button
        content = content.replace(
            '                        <!-- Download Spreadsheet button temporarily disabled -->\n                        <!--\n                        <a href="#" \n                           class="btn btn-outline-success" \n                           data-bs-toggle="tooltip" data-bs-placement="top" \n                           title="Download billing spreadsheet">\n                            <i class="fas fa-download me-1"></i> Download Spreadsheet\n                        </a>\n                        -->',
            '                        <a href="{% url \'download_billing_spreadsheet\' %}?search={{ search_query|urlencode }}&sort={{ sort_by|urlencode }}&order={{ sort_order|urlencode }}" \n                           class="btn btn-outline-success" \n                           data-bs-toggle="tooltip" data-bs-placement="top" \n                           title="Download billing spreadsheet">\n                            <i class="fas fa-download me-1"></i> Download Spreadsheet\n                        </a>'
        )
        
        with open(template_file, 'w') as f:
            f.write(content)
        
        # Enable in urls.py
        with open(urls_file, 'r') as f:
            content = f.read()
        
        content = content.replace(
            '    # Download spreadsheet functionality temporarily disabled\n    # path(\'manage-billing/download/\', views.download_billing_spreadsheet, name=\'download_billing_spreadsheet\'),',
            '    path(\'manage-billing/download/\', views.download_billing_spreadsheet, name=\'download_billing_spreadsheet\'),'
        )
        
        with open(urls_file, 'w') as f:
            f.write(content)
        
        # Enable in views.py
        with open(views_file, 'r') as f:
            content = f.read()
        
        content = content.replace(
            '# TEMPORARILY DISABLED - Download spreadsheet functionality\n# @login_required',
            '@login_required'
        )
        
        with open(views_file, 'w') as f:
            f.write(content)
        
        print("✅ Download spreadsheet functionality ENABLED")
        
    else:
        print("Disabling download spreadsheet functionality...")
        
        # Disable in template
        with open(template_file, 'r') as f:
            content = f.read()
        
        # Comment out the button
        content = content.replace(
            '                        <a href="{% url \'download_billing_spreadsheet\' %}?search={{ search_query|urlencode }}&sort={{ sort_by|urlencode }}&order={{ sort_order|urlencode }}" \n                           class="btn btn-outline-success" \n                           data-bs-toggle="tooltip" data-bs-placement="top" \n                           title="Download billing spreadsheet">\n                            <i class="fas fa-download me-1"></i> Download Spreadsheet\n                        </a>',
            '                        <!-- Download Spreadsheet button temporarily disabled -->\n                        <!--\n                        <a href="#" \n                           class="btn btn-outline-success" \n                           data-bs-toggle="tooltip" data-bs-placement="top" \n                           title="Download billing spreadsheet">\n                            <i class="fas fa-download me-1"></i> Download Spreadsheet\n                        </a>\n                        -->'
        )
        
        with open(template_file, 'w') as f:
            f.write(content)
        
        # Disable in urls.py
        with open(urls_file, 'r') as f:
            content = f.read()
        
        content = content.replace(
            '    path(\'manage-billing/download/\', views.download_billing_spreadsheet, name=\'download_billing_spreadsheet\'),',
            '    # Download spreadsheet functionality temporarily disabled\n    # path(\'manage-billing/download/\', views.download_billing_spreadsheet, name=\'download_billing_spreadsheet\'),'
        )
        
        with open(urls_file, 'w') as f:
            f.write(content)
        
        # Disable in views.py
        with open(views_file, 'r') as f:
            content = f.read()
        
        content = content.replace(
            '@login_required',
            '# TEMPORARILY DISABLED - Download spreadsheet functionality\n# @login_required'
        )
        
        with open(views_file, 'w') as f:
            f.write(content)
        
        print("✅ Download spreadsheet functionality DISABLED")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'enable':
        toggle_spreadsheet_download(enable=True)
    else:
        print("Usage: python toggle_spreadsheet_download.py [enable]")
        print("  - No arguments: Show usage")
        print("  - 'enable': Enable the download functionality")
        print("  - Currently: DISABLED")

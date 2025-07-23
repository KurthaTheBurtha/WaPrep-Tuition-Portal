#!/usr/bin/env python3
"""
WaPrep Tuition Portal - Render Deployment Script

This script automates pre-deployment checks and preparation for deploying
to Render, ensuring all requirements are met before deployment.
"""

import os
import sys
import subprocess
import json
import re
from pathlib import Path
from datetime import datetime

class RenderDeploymentChecker:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'warnings': [],
            'errors': [],
            'recommendations': []
        }
    
    def run_all_checks(self):
        """Run all deployment checks"""
        print("🚀 WaPrep Tuition Portal - Render Deployment Check")
        print("=" * 60)
        
        self.check_dependencies()
        self.check_security()
        self.check_database()
        self.check_static_files()
        self.check_environment_variables()
        self.check_git_status()
        self.check_render_config()
        
        self.generate_report()
    
    def check_dependencies(self):
        """Check dependencies and requirements"""
        print("📦 Checking Dependencies...")
        
        # Check requirements.txt exists
        requirements_file = self.project_root / 'requirements.txt'
        if not requirements_file.exists():
            self.results['errors'].append('requirements.txt not found')
            return
        
        # Check for security vulnerabilities
        try:
            result = subprocess.run(['pip-audit'], capture_output=True, text=True)
            if result.returncode == 0:
                self.results['checks']['dependencies'] = {
                    'status': 'PASS',
                    'message': 'No security vulnerabilities found'
                }
            else:
                self.results['warnings'].append('Security vulnerabilities found in dependencies')
                self.results['checks']['dependencies'] = {
                    'status': 'WARNING',
                    'message': result.stdout
                }
        except Exception as e:
            self.results['checks']['dependencies'] = {
                'status': 'ERROR',
                'message': f'Could not check dependencies: {str(e)}'
            }
    
    def check_security(self):
        """Run security audit"""
        print("🔒 Running Security Audit...")
        
        try:
            result = subprocess.run([
                'python', 'scripts/security_audit.py'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                self.results['checks']['security'] = {
                    'status': 'PASS',
                    'message': 'Security audit passed'
                }
            else:
                self.results['warnings'].append('Security audit found issues')
                self.results['checks']['security'] = {
                    'status': 'WARNING',
                    'message': result.stdout
                }
        except Exception as e:
            self.results['checks']['security'] = {
                'status': 'ERROR',
                'message': f'Security audit failed: {str(e)}'
            }
    
    def check_database(self):
        """Check database migrations"""
        print("🗄️ Checking Database Migrations...")
        
        try:
            # Check for unapplied migrations
            result = subprocess.run([
                'python', 'manage.py', 'showmigrations'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.returncode == 0:
                # Check for unapplied migrations
                if '[X]' in result.stdout and '[ ]' in result.stdout:
                    self.results['warnings'].append('Unapplied migrations found')
                    self.results['checks']['database'] = {
                        'status': 'WARNING',
                        'message': 'Some migrations are not applied'
                    }
                else:
                    self.results['checks']['database'] = {
                        'status': 'PASS',
                        'message': 'All migrations are applied'
                    }
            else:
                self.results['checks']['database'] = {
                    'status': 'ERROR',
                    'message': 'Could not check migrations'
                }
        except Exception as e:
            self.results['checks']['database'] = {
                'status': 'ERROR',
                'message': f'Database check failed: {str(e)}'
            }
    
    def check_static_files(self):
        """Check static files configuration"""
        print("📁 Checking Static Files...")
        
        # Check if collectstatic has been run
        static_root = self.project_root / 'staticfiles'
        if static_root.exists() and any(static_root.iterdir()):
            self.results['checks']['static_files'] = {
                'status': 'PASS',
                'message': 'Static files collected'
            }
        else:
            self.results['recommendations'].append('Run collectstatic before deployment')
            self.results['checks']['static_files'] = {
                'status': 'INFO',
                'message': 'Static files not collected (will be done by Render)'
            }
    
    def check_environment_variables(self):
        """Check environment variables"""
        print("🔧 Checking Environment Variables...")
        
        # Check .env file exists
        env_file = self.project_root / '.env'
        if env_file.exists():
            self.results['checks']['environment'] = {
                'status': 'PASS',
                'message': '.env file exists'
            }
        else:
            self.results['recommendations'].append('Create .env file with production variables')
            self.results['checks']['environment'] = {
                'status': 'WARNING',
                'message': '.env file not found'
            }
        
        # Check for hardcoded secrets
        settings_file = self.project_root / 'tuition' / 'settings.py'
        if settings_file.exists():
            with open(settings_file, 'r') as f:
                content = f.read()
            
            # Look for potential hardcoded secrets
            hardcoded_patterns = [
                r'SECRET_KEY\s*=\s*[\'"][^\'"]+[\'"]',
                r'password\s*=\s*[\'"][^\'"]+[\'"]',
                r'api_key\s*=\s*[\'"][^\'"]+[\'"]'
            ]
            
            hardcoded_secrets = []
            for pattern in hardcoded_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    hardcoded_secrets.append(pattern)
            
            if hardcoded_secrets:
                self.results['errors'].append('Hardcoded secrets found in settings')
                self.results['checks']['hardcoded_secrets'] = {
                    'status': 'ERROR',
                    'message': 'Hardcoded secrets found'
                }
            else:
                self.results['checks']['hardcoded_secrets'] = {
                    'status': 'PASS',
                    'message': 'No hardcoded secrets found'
                }
    
    def check_git_status(self):
        """Check git status"""
        print("📝 Checking Git Status...")
        
        try:
            # Check if there are uncommitted changes
            result = subprocess.run([
                'git', 'status', '--porcelain'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            if result.stdout.strip():
                self.results['warnings'].append('Uncommitted changes found')
                self.results['checks']['git_status'] = {
                    'status': 'WARNING',
                    'message': 'Uncommitted changes detected'
                }
            else:
                self.results['checks']['git_status'] = {
                    'status': 'PASS',
                    'message': 'All changes committed'
                }
            
            # Check current branch
            result = subprocess.run([
                'git', 'branch', '--show-current'
            ], capture_output=True, text=True, cwd=self.project_root)
            
            current_branch = result.stdout.strip()
            self.results['checks']['git_branch'] = {
                'status': 'INFO',
                'message': f'Current branch: {current_branch}'
            }
            
        except Exception as e:
            self.results['checks']['git_status'] = {
                'status': 'ERROR',
                'message': f'Git check failed: {str(e)}'
            }
    
    def check_render_config(self):
        """Check Render-specific configuration"""
        print("🎯 Checking Render Configuration...")
        
        # Check for build.sh
        build_script = self.project_root / 'build.sh'
        if build_script.exists():
            self.results['checks']['build_script'] = {
                'status': 'PASS',
                'message': 'build.sh found'
            }
        else:
            self.results['recommendations'].append('Create build.sh for custom build process')
            self.results['checks']['build_script'] = {
                'status': 'INFO',
                'message': 'build.sh not found (using default build)'
            }
        
        # Check for runtime.txt
        runtime_file = self.project_root / 'runtime.txt'
        if runtime_file.exists():
            with open(runtime_file, 'r') as f:
                runtime = f.read().strip()
            self.results['checks']['runtime'] = {
                'status': 'PASS',
                'message': f'Python runtime specified: {runtime}'
            }
        else:
            self.results['recommendations'].append('Create runtime.txt to specify Python version')
            self.results['checks']['runtime'] = {
                'status': 'INFO',
                'message': 'runtime.txt not found (using default Python)'
            }
        
        # Check for Procfile
        procfile = self.project_root / 'Procfile'
        if procfile.exists():
            with open(procfile, 'r') as f:
                procfile_content = f.read()
            self.results['checks']['procfile'] = {
                'status': 'PASS',
                'message': 'Procfile found'
            }
        else:
            self.results['recommendations'].append('Create Procfile for custom start command')
            self.results['checks']['procfile'] = {
                'status': 'INFO',
                'message': 'Procfile not found (using default start command)'
            }
    
    def generate_report(self):
        """Generate deployment report"""
        print("\n" + "=" * 60)
        print("📋 DEPLOYMENT CHECK REPORT")
        print("=" * 60)
        
        # Count results
        total_checks = len(self.results['checks'])
        passed_checks = sum(1 for check in self.results['checks'].values() if check.get('status') == 'PASS')
        warning_checks = sum(1 for check in self.results['checks'].values() if check.get('status') == 'WARNING')
        error_checks = sum(1 for check in self.results['checks'].values() if check.get('status') == 'ERROR')
        
        print(f"Total Checks: {total_checks}")
        print(f"✅ Passed: {passed_checks}")
        print(f"⚠️ Warnings: {warning_checks}")
        print(f"❌ Errors: {error_checks}")
        print(f"🚨 Errors Found: {len(self.results['errors'])}")
        print(f"💡 Recommendations: {len(self.results['recommendations'])}")
        
        # Show errors
        if self.results['errors']:
            print("\n🚨 ERRORS (Must Fix Before Deployment):")
            for i, error in enumerate(self.results['errors'], 1):
                print(f"{i}. {error}")
        
        # Show warnings
        if self.results['warnings']:
            print("\n⚠️ WARNINGS (Should Address):")
            for i, warning in enumerate(self.results['warnings'], 1):
                print(f"{i}. {warning}")
        
        # Show recommendations
        if self.results['recommendations']:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(self.results['recommendations'], 1):
                print(f"{i}. {rec}")
        
        # Show detailed check results
        print("\n📊 DETAILED CHECK RESULTS:")
        for check_name, check_result in self.results['checks'].items():
            status_icon = {
                'PASS': '✅',
                'WARNING': '⚠️',
                'ERROR': '❌',
                'INFO': 'ℹ️'
            }.get(check_result['status'], '❓')
            
            print(f"{status_icon} {check_name}: {check_result['message']}")
        
        # Save report
        report_file = self.project_root / 'deployment_check_report.json'
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Deployment readiness
        if len(self.results['errors']) == 0:
            print("\n🎉 DEPLOYMENT READY!")
            print("Your application is ready for deployment to Render.")
            print("\nNext steps:")
            print("1. Push your code to Git repository")
            print("2. Create Render service and configure environment variables")
            print("3. Deploy and monitor the deployment process")
        else:
            print(f"\n⚠️ DEPLOYMENT NOT READY")
            print(f"Please fix {len(self.results['errors'])} error(s) before deploying.")

def main():
    """Main function"""
    checker = RenderDeploymentChecker()
    checker.run_all_checks()

if __name__ == '__main__':
    main() 
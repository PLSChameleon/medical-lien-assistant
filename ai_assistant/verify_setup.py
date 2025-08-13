#!/usr/bin/env python3
"""
Verification script to check if all components are working
Run this after setup to verify everything is correctly configured
"""

import os
import sys
import importlib.util

def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} MISSING: {filepath}")
        return False

def check_import(module_name, description):
    """Check if a module can be imported"""
    try:
        if '.' in module_name:
            # Handle nested imports
            parts = module_name.split('.')
            parent = __import__(parts[0])
            for part in parts[1:]:
                parent = getattr(parent, part)
        else:
            __import__(module_name)
        print(f"✅ {description} import works")
        return True
    except ImportError as e:
        print(f"❌ {description} import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ {description} import error: {e}")
        return False

def main():
    """Main verification function"""
    print("🔍 AI Assistant Setup Verification")
    print("=" * 50)
    
    success_count = 0
    total_checks = 0
    
    # Check critical files exist
    files_to_check = [
        ("config.py", "Configuration module"),
        ("main_new.py", "New main application"),
        ("setup.py", "Setup script"),
        ("requirements.txt", "Dependencies file"),
        ("config.env", "Environment variables"),
        ("config.env.example", "Environment template"),
        ("services/__init__.py", "Services package init"),
        ("services/gmail_service.py", "Gmail service"),
        ("services/ai_service.py", "AI service"),
        ("utils/__init__.py", "Utils package init"),
        ("utils/logging_config.py", "Logging utilities"),
        ("test_basic.py", "Basic tests"),
        (".gitignore", "Git ignore file"),
    ]
    
    print("\n📁 File Structure Check:")
    for filepath, description in files_to_check:
        if check_file_exists(filepath, description):
            success_count += 1
        total_checks += 1
    
    # Check Python imports
    print("\n🐍 Python Import Check:")
    imports_to_check = [
        ("config", "Configuration"),
        ("case_manager", "Case Manager"),
        ("services.gmail_service", "Gmail Service module"),
        ("services.ai_service", "AI Service module"),
        ("utils.logging_config", "Logging Config module"),
        ("services", "Services package"),
        ("utils", "Utils package"),
    ]
    
    for module_name, description in imports_to_check:
        if check_import(module_name, description):
            success_count += 1
        total_checks += 1
    
    # Check environment setup
    print("\n🔧 Environment Check:")
    
    # Check if config.env has been customized
    try:
        with open("config.env", "r") as f:
            content = f.read()
            if "your_openai_api_key_here" in content:
                print("⚠️  config.env still has placeholder values - needs customization")
            else:
                print("✅ config.env has been customized")
                success_count += 1
    except Exception as e:
        print(f"❌ Error reading config.env: {e}")
    total_checks += 1
    
    # Check for credentials.json
    if check_file_exists("credentials.json", "Google OAuth credentials"):
        success_count += 1
    total_checks += 1
    
    # Check data directory
    if check_file_exists("data", "Data directory"):
        success_count += 1
    total_checks += 1
    
    # Final summary
    print("\n" + "=" * 50)
    print(f"📊 Verification Results: {success_count}/{total_checks} checks passed")
    
    if success_count == total_checks:
        print("🎉 Perfect! Everything looks good.")
        print("✅ Ready to run: python main_new.py")
    elif success_count >= total_checks * 0.8:  # 80% success
        print("🟡 Good! Most components are working.")
        print("🔧 Fix the failing items above, then you're ready to go.")
    else:
        print("🔴 Issues found. Please address the failing checks above.")
        print("💡 Try running: python setup.py")
    
    print("\n📚 Next Steps:")
    print("1. Customize config.env with your API keys")
    print("2. Add credentials.json from Google Cloud Console")
    print("3. Place your cases Excel file in data/ directory")
    print("4. Run: python main_new.py")

if __name__ == "__main__":
    main()
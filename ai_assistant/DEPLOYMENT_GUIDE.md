# Medical Lien Assistant - Deployment Guide

## 🚀 Quick Start for Non-Technical Users

### Option 1: Simplest Installation (Recommended)
1. **Download** the `ai_assistant` folder to your computer
2. **Double-click** `INSTALL.bat`
3. **Wait** 10-15 minutes for automatic setup
4. **Find** "Medical Lien Assistant" on your desktop
5. **Double-click** to start using!

That's it! No technical knowledge needed.

---

## 📦 Deployment Options

### 1. **Automated Installer (INSTALL.bat)**
- **Best for:** Non-technical users
- **What it does:** 
  - Automatically installs Python if needed
  - Installs all dependencies
  - Creates desktop shortcuts
  - Sets up everything automatically
- **How to use:** Just double-click `INSTALL.bat`
- **Time:** 10-15 minutes first time, instant thereafter

### 2. **Standalone Executable (Coming Soon)**
- **Best for:** Users who can't install Python
- **What it does:** Single .exe file with everything included
- **How to create:**
  ```batch
  cd ai_assistant
  python build_standalone.py
  ```
- **Result:** `dist/MedicalLienAssistant.exe` (no Python needed!)

### 3. **Portable Package**
- **Best for:** USB drives, shared computers
- **What it includes:** Everything needed in one folder
- **How to use:** Extract ZIP and run

---

## 🛠️ For IT Administrators

### Pre-Installation Requirements
- **Operating System:** Windows 10/11 (64-bit)
- **Storage:** 2 GB free space
- **Network:** Internet connection for initial setup
- **Permissions:** Local admin (for Python installation only)

### Silent Installation
For mass deployment, use the PowerShell script:
```powershell
powershell.exe -ExecutionPolicy Bypass -File Install_Assistant.ps1
```

### Group Policy Deployment
1. Copy `ai_assistant` folder to network share
2. Create GPO with startup script pointing to `\\server\share\ai_assistant\INSTALL.bat`
3. Apply to target computers

### System Requirements Installed
- Python 3.11 (if not present)
- Required Python packages (see requirements.txt)
- Chromium browser (for CMS automation)

---

## 👥 For End Users

### First Time Setup
When you first run Medical Lien Assistant:

1. **Setup Wizard appears automatically**
2. **Gmail Setup:**
   - Enter your Gmail address
   - Click "Authorize Gmail"
   - Sign in to Google in the browser
   - Grant permissions
   - Copy the code back to the wizard
3. **CMS Setup:**
   - Enter your Transcon username
   - Enter your Transcon password
   - Click "Test Connection" (optional)
4. **Done!** Your credentials are saved securely

### Daily Use
- Double-click desktop icon
- Select your username (if multiple users)
- Click "Login"
- Start processing cases!

---

## 📋 Deployment Checklist

### For Deploying to New Users:

#### Preparation
- [ ] Download/copy `ai_assistant` folder
- [ ] Ensure `credentials.json` is included
- [ ] Verify internet connection available

#### Installation  
- [ ] Run `INSTALL.bat` as the user (not admin)
- [ ] Wait for installation to complete (10-15 min)
- [ ] Verify desktop shortcut created

#### Setup
- [ ] Launch Medical Lien Assistant
- [ ] Complete Gmail authentication
- [ ] Enter CMS credentials
- [ ] Test with one case

#### Verification
- [ ] Can fetch emails from Gmail
- [ ] Can login to CMS
- [ ] Can process a test case
- [ ] Credentials saved for next session

---

## 🔧 Troubleshooting

### "Python installation failed"
- Run `INSTALL.bat` as Administrator
- Or manually install Python from python.org

### "Can't find Medical Lien Assistant"
- Check Desktop for shortcut
- Check Start Menu > Programs
- Navigate to folder and run `multi_user_launcher.py`

### "Gmail authentication failed"
- Check internet connection
- Ensure pop-ups are allowed
- Try using Chrome as default browser

### "CMS login not working"
- Verify username/password are correct
- Check if CMS website is accessible
- Try "Test Connection" in setup wizard

---

## 📁 File Structure

```
ai_assistant/
├── INSTALL.bat              # One-click installer
├── Install_Assistant.ps1    # PowerShell installer script
├── multi_user_launcher.py   # Main application
├── credentials.json         # Gmail API configuration
├── requirements.txt         # Python dependencies
└── [other Python files]     # Application code
```

---

## 🔐 Security Notes

- **Credentials are encrypted** using industry standards
- **Stored locally** in user's AppData folder
- **Never transmitted** except to Gmail/CMS directly
- **Each user** has separate encrypted storage
- **No admin rights** needed after Python installation

---

## 📞 Support

For issues or questions:
1. Check the logs in `logs/` folder
2. Run "Test Connection" in setup wizard
3. Try re-running `INSTALL.bat`
4. Contact your IT administrator

---

## ✅ Quick Validation

After deployment, verify success by:
1. Desktop shortcut exists
2. Application launches
3. Setup wizard appears (first time)
4. Can authenticate with Gmail
5. Can enter CMS credentials
6. Can process a test case

---

## 🎯 Deployment Best Practices

1. **Test on one machine first** before mass deployment
2. **Have user credentials ready** for initial setup
3. **Allocate 30 minutes** for first-time setup per user
4. **Document any organization-specific settings**
5. **Create a test case** for validation

---

## 📊 Deployment Metrics

Typical installation times:
- Python installation: 3-5 minutes
- Dependencies installation: 5-10 minutes  
- Browser components: 2-3 minutes
- Total first-time setup: 10-15 minutes
- Subsequent launches: < 5 seconds

Storage requirements:
- Python: ~300 MB
- Dependencies: ~500 MB
- Browser components: ~400 MB
- Application: ~50 MB
- Total: ~1.3 GB

---

This guide ensures anyone can deploy the Medical Lien Assistant successfully, regardless of technical expertise!
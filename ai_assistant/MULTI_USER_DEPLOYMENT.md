# Multi-User Deployment Guide

## Overview
The Medical Lien Assistant now supports multiple users with individual Gmail and CMS credentials. Each user's credentials are encrypted and stored securely on their local machine.

## Deployment Steps for New Users

### 1. Prerequisites
- Python 3.8 or higher
- Windows/Mac/Linux operating system
- Gmail account
- CMS (Transcon Financial) account

### 2. Installation

#### Step 1: Copy Application Files
Copy the entire `ai_assistant` folder to the new user's computer.

#### Step 2: Install Dependencies
Open a terminal/command prompt in the `ai_assistant` directory and run:
```bash
pip install -r requirements.txt
```

#### Step 3: Install Playwright Browsers
```bash
playwright install chromium
```

### 3. Configuration

#### Step 1: Ensure Gmail API Project Files
Make sure the following file exists in the `ai_assistant` directory:
- `credentials.json` - This is the Gmail API project credentials file (same for all users)

#### Step 2: Launch the Application
Run the multi-user launcher:
```bash
python multi_user_launcher.py
```

### 4. First-Time Setup

When a new user runs the application for the first time:

1. **Setup Wizard** will automatically launch
2. **Gmail Setup**:
   - Enter Gmail address
   - Click "Authorize Gmail"
   - Browser opens → Sign in to Google
   - Grant permissions to the app
   - Copy the authorization code
   - Paste it back in the wizard
   - Click "Verify Code"

3. **CMS Setup**:
   - Enter CMS username
   - Enter CMS password
   - Click "Test CMS Connection" (optional)
   - Credentials are encrypted and saved

4. **Complete Setup**:
   - Click "Finish"
   - Application launches with user's credentials

### 5. Subsequent Launches

After initial setup:
1. Run `python multi_user_launcher.py`
2. Select your user account from the dropdown
3. Click "Login"
4. Application launches with your saved credentials

## Important Notes

### Gmail API Project
- All users share the same Gmail API project (credentials.json)
- Each user authenticates their own Gmail account
- OAuth tokens are stored separately per user

### Credential Storage
- Credentials are encrypted using industry-standard encryption
- Stored in user-specific directories:
  - Windows: `%APPDATA%\MedicalLienAssistant\`
  - macOS: `~/Library/Application Support/MedicalLienAssistant/`
  - Linux: `~/.config/MedicalLienAssistant/`
- Each user only has access to their own credentials

### Security
- CMS passwords are encrypted before storage
- Gmail tokens use Google's OAuth2 security
- Credentials never leave the local machine
- No credentials are stored in the application code

## Running the Application

### Option 1: Multi-User Launcher (Recommended)
```bash
python multi_user_launcher.py
```
This provides user selection and ensures proper credential loading.

### Option 2: Direct Launch (Original Method)
```bash
python main_new.py
```
This uses environment variables or defaults (less secure for multi-user).

## Troubleshooting

### "No Gmail token found"
- User needs to complete Gmail authentication
- Run the setup wizard again or use "Add New User"

### "CMS credentials not configured"
- User needs to enter CMS credentials
- Use the setup wizard to configure

### "Failed to refresh Gmail token"
- Token may have expired
- Re-authenticate through the setup wizard

### Multiple Users on Same Computer
- Each Windows/Mac/Linux user account has separate credentials
- Users cannot see each other's credentials
- Application data is isolated per system user

## Adding Additional Users

1. Run `python multi_user_launcher.py`
2. Click "Add New User"
3. Complete the setup wizard
4. New user is added to the user list

## Removing User Credentials

User credentials can be manually removed by deleting:
- Windows: `%APPDATA%\MedicalLienAssistant\`
- macOS: `~/Library/Application Support/MedicalLienAssistant/`
- Linux: `~/.config/MedicalLienAssistant/`

## Support

For issues or questions:
1. Check the application logs in the `logs/` directory
2. Verify all prerequisites are installed
3. Ensure `credentials.json` is present
4. Try re-running the setup wizard
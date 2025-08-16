# Error Reporting Setup Guide

## Overview
The Medical Lien Assistant includes comprehensive error tracking to help diagnose issues during testing and deployment.

## How Error Reporting Works

### 1. **Local Error Logging** (Default)
- Errors are automatically saved to `logs/errors/` directory
- Each user has their own error log file
- Logs are kept for 7 days then auto-deleted

### 2. **Manual Export**
Users can export error reports:
1. Go to `Tools → View Logs`
2. Click "Export Full Error Report"
3. Save the file and email it to support

### 3. **Automatic Error Reporting** (Optional)
Configure automatic email reports for critical errors.

## Setting Up Automatic Error Reporting

### Option 1: Email Auto-Send (Recommended)

1. **Edit Configuration**
   Create a file `data/error_config.json`:
   ```json
   {
     "admin_email": "your-email@example.com",
     "auto_send_errors": true,
     "severity_threshold": "ERROR",
     "send_critical_immediately": true
   }
   ```

2. **The system will automatically:**
   - Email you when CRITICAL errors occur
   - Batch ERROR level issues and send summaries
   - Include full stack traces and system info

### Option 2: Shared Network Drive

1. **Set up a shared folder** all collectors can access:
   ```
   \\YourServer\SharedDrive\MedicalLienErrors\
   ```

2. **Configure in the app:**
   - Errors will auto-save to the shared location
   - You can monitor all errors from one place

### Option 3: Cloud Storage (Google Drive)

Since you're using Gmail, errors can auto-upload to Google Drive:

1. **Create a shared folder** in Google Drive
2. **Share it** with all collectors
3. **Errors auto-sync** to the cloud

## What Gets Tracked

### Error Information:
- **User**: Email of the person who encountered the error
- **Timestamp**: Exact time of the error
- **Error Type**: Type of exception (FileNotFoundError, etc.)
- **Location**: File, line number, and function
- **Context**: What the user was trying to do
- **Stack Trace**: Full technical details
- **System Info**: OS, Python version, etc.

### Example Error Report:
```
ERROR REPORT - 2025-08-16 14:30:00
User: collector@example.com
Session: 20250816_143000

Error: FileNotFoundError
Message: [Errno 2] No such file or directory: 'cases.xlsx'
Context: Loading spreadsheet for bulk processing
Location: case_manager.py:26 in load_cases()

Stack Trace:
  File "enhanced_gui_app.py", line 1873, in load_spreadsheet
    self.case_manager = CaseManager(filepath)
  File "case_manager.py", line 26, in __init__
    df = pd.read_excel(self.filepath)
    
System: Windows 10, Python 3.9.7
```

## For Testing Phase

### Setup for Your Test Collector:

1. **Before giving them the program**, configure error reporting:
   ```python
   # In enhanced_gui_app.py, add your email
   ADMIN_EMAIL = "your-email@example.com"
   ```

2. **They will see user-friendly messages** when errors occur:
   - "An error occurred and has been logged"
   - "Error Code: SESSION_ID_12345"

3. **You will receive:**
   - Automatic email for critical errors
   - Daily summary of all errors
   - Full technical details for debugging

## Viewing Error Logs

### In the Application:
1. **Tools → View Logs**
   - Activity Log: All user actions
   - Error Log: All errors with counts
   - System Info: Configuration details

2. **Tools → Export Error Report**
   - Creates a shareable text file
   - Includes last 5 errors in detail
   - Ready to email or upload

### Direct File Access:
```
ai_assistant/
├── logs/
│   ├── errors/
│   │   ├── errors_collector1@email_20250816.json
│   │   ├── errors_collector2@email_20250816.json
│   │   └── error_report_20250816_143000.txt
│   └── assistant_20250816.log
```

## Privacy & Security

- **No sensitive data** is included in error reports
- **Passwords/credentials** are never logged
- **Case data** is not included unless relevant to the error
- **Local storage** by default - no data leaves the machine unless configured

## Quick Troubleshooting

### If a collector reports an issue:

1. **Ask them to:**
   - Go to Tools → Export Error Report
   - Send you the file

2. **The report will tell you:**
   - Exactly what went wrong
   - When it happened
   - What they were doing
   - How to reproduce it

3. **You can then:**
   - Fix the issue
   - Push an update
   - They restart the program

## Support Contact

If you need help interpreting error reports or fixing issues:
1. Export the error report
2. Include the session ID
3. Describe what the user was trying to do

The error tracking system ensures you'll have all the information needed to quickly diagnose and resolve any issues that arise during testing.
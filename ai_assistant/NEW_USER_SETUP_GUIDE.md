# 📋 **Medical Lien Assistant - New User Setup Guide**

## **Phase 1: Initial Installation (10-15 minutes)**

**Step 1: Download the Application**
- You'll receive a folder called `ai_assistant` from your administrator
- Save it to your C: drive or Documents folder
- Make sure the folder contains `EASY_SETUP.bat` and `credentials.json`

**Step 2: Run the Easy Installer**
1. Navigate to the `ai_assistant` folder
2. **Double-click** `EASY_SETUP.bat`
3. When Windows asks "Do you want to allow this app to make changes?", click **YES**
4. The installer will:
   - ✅ Check if Python is installed (installs it if needed - adds 5 minutes)
   - ✅ Install all required packages (PyQt5, Google APIs, OpenAI, etc.)
   - ✅ Install browser components for CMS integration
   - ✅ Create a desktop shortcut called "Medical Lien Assistant"
5. Wait for "Setup Complete!" message
6. Press any key to close the installer

---

## **Phase 2: First-Time User Setup (5 minutes)**

**Step 3: Launch the Application**
1. **Double-click** the "Medical Lien Assistant" shortcut on your desktop
2. A **User Selection Dialog** will appear
3. Click **"Add New User"** button

**Step 4: Gmail Authentication**
The Setup Wizard opens automatically:
1. **Enter your work Gmail address** (e.g., yourname@prohealth.com)
2. Click **"Authenticate Gmail"**
3. Your browser opens → **Sign in with your Gmail account**
4. Google shows permissions screen → Click **"Continue"** then **"Allow"**
5. Browser shows "Authentication successful!" → You can close the browser
6. The wizard shows ✅ "Gmail authenticated successfully"

**Step 5: CMS Credentials Setup**
Still in the Setup Wizard:
1. **Enter your CMS username** (same one you use for the CMS website)
2. **Enter your CMS password**
3. Click **"Test CMS Connection"**
4. Wait 10-15 seconds for verification
5. You'll see ✅ "CMS connection successful"
6. Click **"Complete Setup"**

---

## **Phase 3: Loading Your Work Data (2 minutes)**

**Step 6: Upload Your Spreadsheet**
After the wizard closes, the main application opens:
1. Click **File** menu → **Upload Spreadsheet**
2. Navigate to your collector cases Excel file
3. Select your `.xlsx` or `.xls` file
4. Click **Open**
5. Progress bar shows "Processing spreadsheet..."
6. You'll see "✅ Loaded X cases successfully"

**Step 7: Initial Email History Download**
One-time setup to sync your email history:
1. Click **Tools** menu → **Download Email History**
2. This downloads your last 30 days of emails
3. Progress bar shows "Downloading emails... (this may take 10-30 minutes)"
4. You can use other features while this runs in background

---

## **Phase 4: Daily Use**

**Starting the Program Each Day:**
- Simply double-click "Medical Lien Assistant" on your desktop
- Select your email from the dropdown
- Click **Login**
- The program remembers everything - no need to re-enter credentials!

**Main Features Available:**

📧 **Email Tab**
- **Categorize Cases** - Automatically sorts cases by priority
- **Generate Emails** - Creates follow-ups based on case status
- **Send Emails** - Review and send in batches

⏰ **Stale Cases Tab**
- Shows cases with no contact in 30+ days
- Red highlights for 60+ days
- One-click email generation

📊 **Bulk Email Tab**
- Process multiple cases at once
- Select templates (Follow-up, Status Request, etc.)
- Batch send with preview

✅ **Acknowledged Tab**
- Track which cases have been contacted
- See email history per case
- Monitor response rates

---

## **🛠️ Troubleshooting Common Issues**

**"Can't find EASY_SETUP.bat"**
- Make sure you're in the `ai_assistant` folder
- File might be named `INSTALL_SIMPLE.bat` instead

**"Gmail authentication opens but nothing happens"**
- Check you're using your default browser
- Clear browser cache and cookies
- Try using Chrome or Edge

**"CMS connection failed"**
- Verify username/password are correct
- Check your internet connection
- Try logging into CMS website first to ensure account is active

**"Spreadsheet won't upload"**
- Close the file in Excel first
- Ensure it's .xlsx or .xls format (not .csv)
- Check that it has the required columns (Collector, Status, etc.)

---

## **✨ Pro Tips for New Users**

1. **Run the program as Administrator** if you encounter permission issues
2. **Keep your spreadsheet updated** - upload a fresh one weekly
3. **Use Categorize before generating emails** for better organization
4. **The program auto-saves** - you won't lose work if it closes
5. **Check Stale Cases daily** - these are your priority follow-ups
6. **Email best practices:**
   - Send Tuesday-Thursday, 10am-2pm for best response rates
   - Keep subject lines under 50 characters
   - Always review before sending

---

## **📞 Getting Help**

- **Technical issues:** Run `CHECK_INSTALL.bat` for diagnostics
- **Error messages:** Check `logs/assistant.log` for details
- **Setup problems:** Run `DIAGNOSE.bat` to identify issues
- **Team support:** Contact your administrator with the error details

The system is designed to be user-friendly with clear buttons and tooltips. Most features are self-explanatory once you start using them!

---

*Version 2.0 - Last Updated: January 2025*
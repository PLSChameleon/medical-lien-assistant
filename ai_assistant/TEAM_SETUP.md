# ProHealth Email Assistant - Team Setup Guide

## Quick Setup for Team Members

### What You Need
1. The program folder with `credentials.json` (get from Dean)
2. Your work Gmail account
3. About 5 minutes

### Setup Steps

1. **Run the program**
   ```
   python main_new.py
   ```

2. **Run Gmail setup command**
   ```
   > gmail setup
   ```

3. **Authorize your Gmail**
   - A browser window will open
   - Log in with your work Gmail
   - Click "Continue" when you see the app
   - Grant the permissions

4. **Enter your name**
   - Just your full name (e.g., "John Smith")
   - The program will detect everything else

5. **You're done!**
   - Your Gmail is now connected
   - Your signature will be used automatically
   - All emails will come from your account

### First Time Use

After setup, run these commands:

1. **Download your email history** (one time, takes 10-30 minutes)
   ```
   > bootstrap emails
   ```

2. **Analyze your emails** (fast, takes seconds)
   ```
   > bootstrap collections
   ```

3. **Start using the features!**
   ```
   > help
   ```

### Important Notes

- ✅ You DON'T need to create a Google Cloud project
- ✅ You DON'T need to enable any APIs
- ✅ You DON'T need to download credentials
- ✅ Your Gmail signature is used automatically
- ✅ All emails come from YOUR Gmail account

### Troubleshooting

**"credentials.json not found"**
- Get this file from Dean
- Put it in the same folder as main_new.py

**"Authorization failed"**
- Make sure you're using your work Gmail
- Try a different browser
- Contact Dean for help

**Need to switch Gmail accounts?**
```
python team_gmail_setup.py --reset
```
Then run `gmail setup` again

### Security

- Your Gmail password is NEVER stored
- Only OAuth tokens are saved (industry standard)
- You can revoke access anytime from your Google account settings
- The app only has permission to read/send emails

### Questions?

Contact Dean for any setup issues or to get the credentials.json file.
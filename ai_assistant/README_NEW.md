# 🤖 AI Assistant for Medical Lien Case Management

An intelligent assistant that helps manage medical lien cases by automating email analysis, case summarization, and follow-up communications using AI.

## ✨ Features

- **Case Management**: Load and search cases from Excel spreadsheets
- **Email Integration**: Search Gmail for case-related conversations
- **AI-Powered Analysis**: Generate summaries and draft professional emails using GPT-4
- **Smart Follow-ups**: Draft contextual follow-up emails based on conversation history
- **Status Requests**: Generate professional status inquiry emails
- **Secure Configuration**: Environment-based configuration management
- **Comprehensive Logging**: Track all activities and sent emails

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Gmail account with API access
- OpenAI API key
- Excel file with case data

### Automated Setup

1. **Run the setup script:**
   ```bash
   python setup.py
   ```

2. **Configure your environment:**
   - Edit `config.env` with your API keys
   - Add your `credentials.json` from Google Cloud Console
   - Place your cases Excel file in the `data/` directory

3. **Start the assistant:**
   ```bash
   python main_new.py
   ```

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp config.env.example config.env
   # Edit config.env with your actual API keys
   ```

3. **Set up Google OAuth:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Download `credentials.json` to project root

4. **Add your case data:**
   - Place your cases Excel file in the `data/` directory
   - Update `CASES_FILE_PATH` in `config.env` if needed

## 📋 Usage

The assistant provides an interactive command-line interface:

### Available Commands

```bash
# Summarize a case and related emails
summarize pv 123456
summarize John Doe

# Draft follow-up emails
draft follow-up for 123456

# Create status request emails
draft status request for 123456

# Exit the application
exit
```

### Example Session

```
🤖 Welcome to your AI Case Assistant!
> summarize pv 123456

📄 Case Summary:
Patient: John Doe
PV #: 123456 | CMS: 987654
Date of Injury: 2024-01-15
Attorney Email: attorney@lawfirm.com
Law Firm: Smith & Associates

🔍 Searching for related emails...
📬 Found 3 related emails

🧠 Generating AI summary...
📄 Summary:
• Initial medical records request sent on 2024-01-20
• Attorney acknowledged receipt on 2024-01-22
• Follow-up needed for outstanding documentation

Recommendation: Send follow-up requesting specific missing documents.
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPEN_AI_API_KEY` | OpenAI API key | Yes |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | Optional |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | Optional |
| `CASES_FILE_PATH` | Path to Excel file with cases | No (defaults to data/cases.xlsx) |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No (defaults to INFO) |
| `MAX_EMAIL_RESULTS` | Max emails to search | No (defaults to 10) |

### Case Data Format

Your Excel file should have the following columns (0-indexed):
- Column 0: CMS Number
- Column 1: PV Number
- Column 2: Status
- Column 3: Patient Name
- Column 4: Date of Injury
- Column 12: Law Firm
- Column 18: Attorney Email
- Column 19: Attorney Phone

## 📁 Project Structure

```
ai_assistant/
├── config.py              # Configuration management
├── main_new.py            # Main application (NEW - use this!)
├── main.py               # Legacy main file (backup)
├── case_manager.py       # Case data management
├── setup.py              # Automated setup script
├── requirements.txt      # Python dependencies
├── config.env.example    # Environment template
├── services/
│   ├── gmail_service.py  # Gmail API wrapper
│   └── ai_service.py     # OpenAI API wrapper
├── utils/
│   └── logging_config.py # Logging utilities
├── logs/                 # Application logs
└── data/                 # Case data files
```

## 🔒 Security Features

- Environment-based configuration (no hardcoded secrets)
- Comprehensive `.gitignore` for sensitive files
- Secure credential handling
- Activity logging for audit trails

## 🐛 Troubleshooting

### Common Issues

1. **"No valid Gmail token found"**
   - Make sure `credentials.json` is in the project root
   - Run the application to trigger OAuth flow

2. **"OpenAI API key not found"**
   - Check your `config.env` file
   - Ensure `OPEN_AI_API_KEY` is set correctly

3. **"Cases file not found"**
   - Place your Excel file in the `data/` directory
   - Update `CASES_FILE_PATH` in `config.env`

4. **Import errors**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`

### Getting Help

- Check the logs in the `logs/` directory for detailed error information
- Ensure all API keys are valid and have proper permissions
- Verify your Excel file format matches the expected structure

## 🔄 Migrating from Old Version

If you're upgrading from the old `main.py`:

1. **Backup your current setup:**
   ```bash
   cp main.py main_backup.py
   ```

2. **Use the new main file:**
   ```bash
   python main_new.py
   ```

3. **The new version includes:**
   - Better error handling
   - Improved logging
   - Modular architecture
   - Enhanced security

## 📝 Logging

All activities are logged to:
- `logs/assistant_YYYYMMDD.log` - Detailed application logs
- `logs/sent_emails.log` - Record of all sent emails

## ⚡ Performance Tips

- Keep your cases Excel file under 10,000 rows for best performance
- Use specific search terms for faster email retrieval
- Regular log file cleanup (logs older than 30 days)

---

**Ready to streamline your medical lien case management? Run `python setup.py` to get started!**
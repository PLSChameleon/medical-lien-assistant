# Bulk Email Processing Guide

## Overview
The new bulk email processing system allows you to send emails to multiple cases at once with smart categorization, test mode, and batch approval workflows.

## Key Features

### 1. **Test Mode** 🧪
- Send all emails to a test address first to verify content
- Toggle on/off anytime during processing
- Subject lines show "[TEST MODE]" for clarity
- Original recipients preserved in logs

### 2. **Smart Categorization** 📊
- **Never Contacted**: Cases with no email history
- **No Recent Contact**: Cases inactive for 60+ days
- **Missing DOI**: Cases lacking date of injury
- **Old Cases**: Cases older than 2 years
- **By Firm**: Group all cases by law firm

### 3. **Batch Approval Workflow** ✅
- **Preview** emails before sending
- **Approve All**: Send entire batch
- **Select Specific**: Choose individual emails
- **Review Each**: Detailed review with skip option
- **Export**: Save batch to file for external review

### 4. **CMS Integration** 📝
- Automatically queues notes for CMS system
- Test mode adds CMS notes marked with 🧪 TEST MODE
- Production mode adds regular CMS notes
- Run `add session cms notes` to process queued notes
- Tracks all sent emails
- Updates case status in real-time

## Quick Start

### Step 1: Enable Test Mode (Recommended)
```
> bulk test on
Enter test email address (Enter for default): your-email@example.com
✅ Test mode enabled. Emails will go to: your-email@example.com
```

### Step 2: Start Bulk Processing
```
> bulk start
```

This opens the interactive bulk email wizard showing:
- Current mode (TEST/PRODUCTION)
- Available cases by category
- Processing options

### Step 3: Select Processing Method

#### Option A: Process by Category
1. Choose category (e.g., "Never contacted")
2. Set limit (e.g., 10 cases)
3. Review batch preview
4. Approve/reject emails
5. Send approved batch

#### Option B: Process by Firm
1. View firms with cases
2. Select specific firm
3. Set case limit
4. Review and approve
5. Send batch

#### Option C: Custom Selection
1. Enter specific PV numbers
2. Review generated emails
3. Approve and send

### Step 4: Review Results
After sending, you'll see:
- Number of emails sent successfully
- Any failures with error details
- CMS notes queued for processing

### Step 5: Process CMS Notes
After sending emails, process the queued CMS notes:
```
> check pending cms        # See what's waiting
> add session cms notes    # Process all pending
> check pending cms        # Verify all processed
```
This will:
- Add all queued CMS notes to the CMS system
- Test mode notes will be marked with 🧪 TEST MODE
- Production notes will be added normally
- **IMPORTANT**: Emails stay in pending queue until CMS succeeds

## Workflow Examples

### Example 1: Testing with 5 Never-Contacted Cases
```bash
> bulk test on
> bulk start
[Choose option 1: Process by category]
[Choose option 1: Never contacted]
How many to process? 5
[Review the 5 emails]
[Choose A: Approve ALL and send]
```

### Example 2: Send to Specific Law Firm
```bash
> bulk start
[Choose option 2: Process by firm]
[Select firm from list or enter email]
How many cases? [Enter for all]
[Review emails]
[Choose S: Select specific emails]
Enter numbers: 1,3,5-7
```

### Example 3: Quick Status Check
```bash
> bulk stats
📊 Bulk Processing Statistics:
  • Test mode: ON
  • Test email: your-email@example.com
  • Sent this session: 25
  • Total sent (all time): 150
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `bulk start` | Open bulk email wizard |
| `bulk test on` | Enable test mode |
| `bulk test off` | Disable test mode |
| `bulk stats` | Show processing statistics |
| `bulk export` | Export current batch to file |
| `check pending cms` | **CRITICAL**: Check emails waiting for CMS notes |
| `add session cms notes` | **CRITICAL**: Process all pending CMS notes |
| `help` | Show all available commands |

## Best Practices

1. **Always Start in Test Mode**
   - Test with 5-10 emails first
   - Verify content and formatting
   - Check that CMS logging works with 🧪 TEST MODE notes
   - Categories are preserved - you can test the same cases multiple times
   - Test emails don't affect production tracking

2. **Process in Small Batches**
   - Start with 10-20 emails
   - Monitor for any issues
   - Scale up gradually

3. **Use Categories Wisely**
   - Prioritize "Never Contacted" cases
   - Follow up on "No Recent Contact" 
   - Handle "Missing DOI" carefully

4. **Review Before Sending**
   - Use the review options
   - Check recipient addresses
   - Verify case details

## Safety Features

- **Duplicate Prevention**: Won't send to same PV twice
- **Invalid Email Detection**: Skips malformed addresses
- **2099 DOI Handling**: Special handling for unknown dates
- **Session Tracking**: Maintains sent record during session
- **Automatic Logging**: All actions logged for audit
- **CMS Note Protection**: Emails stay in pending queue until CMS note confirmed
- **Never Lost**: Even if CMS fails, emails remain trackable in pending log
- **Recovery System**: Can retry failed CMS notes anytime with `add session cms notes`
- **Status Check**: Use `check pending cms` to see what's waiting

## Troubleshooting

### Emails Not Sending
- Check Gmail authentication: `> init cms`
- Verify email addresses are valid
- Check logs in `logs/sent_emails.log`

### Test Mode Issues
- Ensure test email is valid
- Check spam folder for test emails
- Verify with `bulk stats`

### CMS Notes Not Logging
- Notes are queued for batch processing
- Run `add session cms notes` to process queued notes
- Initialize CMS session: `> init cms`
- Check CMS integration logs
- Verify case data is complete
- Test mode notes will show 🧪 TEST MODE in CMS

## Integration with Existing Features

The bulk email system works seamlessly with:
- **Collections Tracker**: Updates case status automatically
- **Stale Cases**: Removes cases from stale lists after sending
- **Email Cache**: Uses your writing style for consistency
- **AI Service**: Generates contextual email content

## Tips for Maximum Efficiency

1. **Morning Routine**:
   ```
   > bulk test on
   > bulk start
   [Process 10 never-contacted cases in test mode]
   > add session cms notes
   [Verify test CMS notes added correctly with 🧪 marker]
   > bulk test off
   > bulk start
   [Send approved emails in production]
   > add session cms notes
   [Add production CMS notes]
   ```

2. **Weekly Follow-ups**:
   ```
   > list no-recent-contact
   > bulk start
   [Process no-recent-contact category]
   ```

3. **Firm-Specific Campaigns**:
   ```
   > bulk start
   [Process by firm]
   [Select high-volume firms]
   ```

## Data Export

Export batch for manager review:
```
> bulk export
✅ Batch exported to: data/bulk_batch_20250810_143022.json
```

The exported file contains:
- All email details
- Recipients and subjects
- Full email bodies
- Case information

---

## Need Help?

- Type `help` for all commands
- Check `logs/assistant.log` for detailed logs
- Review `logs/sent_emails.log` for send history

Remember: Start small, test thoroughly, then scale up!
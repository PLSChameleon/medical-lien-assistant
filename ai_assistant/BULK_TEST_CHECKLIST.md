# Bulk Email System - Pre-Test Checklist

## 🚀 Before Testing

### 1. **Verify Test Mode Settings**
```
> bulk test on
Enter test email: [YOUR EMAIL]
> bulk stats
```
Confirm it shows TEST MODE: ON

### 2. **Check Your Excel File**
- Ensure `data/cases.xlsx` exists and has data
- Check that PV/PID columns are present
- Verify attorney emails are in the correct column

### 3. **Gmail Authentication**
- Your Gmail credentials are already in the code
- Make sure 2-factor auth app passwords are valid

## 🧪 Test Sequence (Recommended)

### Phase 1: Basic Test (5 emails)
```
> bulk test on
> bulk start
[Choose category: Old cases]
[Process 5 emails]
[Approve all]
> check pending cms
> bulk stats
```

### Phase 2: Verify Email Content
- Check your test inbox for 5 emails
- Verify subject has [TEST MODE] prefix
- Verify content looks correct
- Check DOI formatting (MM/DD/YYYY)

### Phase 3: Test CMS Notes
```
> init cms                    # If not already done
> add session cms notes       # Process pending notes
> check pending cms           # Should show 0 pending
```
Check CMS for notes with 🧪 TEST MODE marker

### Phase 4: Test Different Categories
```
> bulk start
[Try "Never contacted" category]
[Process 3-5 emails]

> bulk start
[Try "By firm" option]
[Select a firm, process 3-5 emails]
```

### Phase 5: Test Batch Approval Options
```
> bulk start
[Generate batch]
[Choose "S" for select specific]
[Enter: 1,3,5]
```
Verify only selected emails are sent

### Phase 6: Verify Category Preservation
```
> bulk start
[Process same category again]
```
The same files should still be available (not marked as sent)

## ⚠️ Known Gotchas

1. **DateTime Fields**: We fixed the `.split()` error, but watch for any date formatting issues

2. **CMS/PID Confusion**: The system uses PID as the primary identifier (sometimes labeled as CMS in the code)

3. **Email Throttling**: System waits 2 seconds between emails to avoid Gmail limits

4. **Batch Size**: Start small (5-10 emails) before processing larger batches

## 📋 Production Readiness Checklist

Before switching to production mode:

- [ ] Test mode emails arrived correctly
- [ ] CMS test notes show 🧪 marker
- [ ] Categories preserved (can re-test same cases)
- [ ] `check pending cms` shows correct counts
- [ ] All pending notes processed successfully
- [ ] Different approval modes work (All/Select/Review)
- [ ] Email content looks professional
- [ ] DOI dates formatted correctly
- [ ] No errors in console

## 🔐 Safety Confirmations

✅ **Test Mode Protection**:
- Emails only go to your test address
- Categories not updated
- Separate test logs

✅ **CMS Protection**:
- Emails stay pending until CMS succeeds
- Can always retry failed notes
- Complete audit trail

✅ **Production Protection**:
- Duplicate PID prevention
- Invalid email detection
- Session tracking

## 📝 Final Commands to Know

```bash
# Check everything
> bulk stats              # Overall statistics
> check pending cms       # Pending CMS notes
> ls logs/                # Check log files

# If something goes wrong
> check pending cms       # See what's pending
> add session cms notes   # Retry CMS notes

# Switch to production (when ready)
> bulk test off
> bulk stats             # Confirm production mode
```

## 🚨 Emergency Stop

If anything goes wrong during testing:
- Press Ctrl+C to stop the program
- Run `check pending cms` to see state
- All emails are logged and recoverable

## 📊 Expected Test Results

After testing 10-20 emails, you should see:
- All test emails in your inbox with [TEST MODE]
- CMS notes with 🧪 TEST MODE markers
- `check pending cms` shows 0 pending
- Categories still show same cases available
- No production tracking affected

## 🎯 Ready for GitHub

Once all tests pass:
1. Document any issues found
2. Clear test logs if desired: `logs/test_emails.log`
3. Keep safety logs: `session_emails_*.log`
4. Commit with clear message about bulk email feature

## 💡 Pro Tips

1. **Keep test mode on** until you're 100% confident
2. **Save test results** - Screenshot successful CMS notes
3. **Note processing time** - How long for 10 emails?
4. **Check spam folder** - Some test emails might go there
5. **Verify firm emails** - Make sure attorney emails are valid

---

## You're Ready! 

The system has multiple safety layers:
- Test mode protection ✅
- Pending queue system ✅
- Category preservation ✅
- CMS note tracking ✅
- Complete logging ✅

Good luck with testing! The system is designed to be safe even if something goes wrong.
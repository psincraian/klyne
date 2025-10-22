# Scripts

This directory contains administrative scripts and maintenance tasks for the Klyne application.

## send_apology_emails.py

Sends apology emails with verification codes to users who registered in the last week.

### Purpose
This script was created to handle a registration error by re-sending verification emails to affected users. It:
- Fetches all users registered in the last 7 days
- Generates fresh verification tokens for each user
- Sends personalized apology emails with verification links
- Logs all actions for auditing

### Usage

From the `app/` directory:

```bash
cd app
uv run python -m src.scripts.send_apology_emails
```

### Safety Features
- Confirmation prompt before sending emails
- Displays environment and domain before execution
- Detailed logging of all operations
- Rate limiting (0.5s delay between emails)
- Error handling for each user individually

### Output
The script will:
1. Ask for confirmation before proceeding
2. Show progress for each user
3. Display a summary of results:
   - Total users found
   - Successfully sent emails
   - Failed emails

### Example Output
```
⚠️  WARNING: This script will send emails to all users registered in the last 7 days.
Environment: production
App Domain: https://klyne.dev

Do you want to proceed? (yes/no): yes

============================================================
APOLOGY EMAIL SCRIPT
============================================================
Environment: production
App Domain: https://klyne.dev
Started at: 2025-10-22T19:26:00+00:00
============================================================
Found 15 users registered in the last 7 days
Processing user: user1@example.com (ID: 123, Registered: 2025-10-20 10:30:00)
✓ Successfully sent apology email to user1@example.com
...
============================================================
APOLOGY EMAIL SEND SUMMARY
============================================================
Total users found: 15
Successfully sent: 15
Failed: 0
============================================================
```

### Requirements
- Resend API key configured in environment
- Database connection
- Users table with created_at timestamps

### Notes
- The script can be run multiple times safely (users will receive multiple emails)
- Verification tokens are regenerated each time
- Tokens expire after 24 hours
- All emails are logged for auditing

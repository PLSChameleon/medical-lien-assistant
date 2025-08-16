"""
Follow-up email template generator
"""

def generate_followup_email(case_data, case_activity=None):
    """
    Generate a follow-up email based on case data and activity
    
    Args:
        case_data: Dictionary containing case information
        case_activity: Optional activity tracking data
    
    Returns:
        Dictionary with email subject and body
    """
    
    # Extract case information
    pv = case_data.get('PV', 'Unknown')
    name = case_data.get('Name', 'Unknown')
    balance = case_data.get('Balance', 0)
    doi = case_data.get('DOI', 'Unknown')
    law_firm = case_data.get('Law Firm', 'Unknown')
    
    # Format balance
    if isinstance(balance, (int, float)):
        balance_str = f"${balance:,.2f}"
    else:
        balance_str = str(balance)
    
    # Determine follow-up context
    if case_activity:
        last_contact = case_activity.get('last_contact')
        sent_count = case_activity.get('sent_count', 0)
        response_count = case_activity.get('response_count', 0)
        
        if response_count == 0 and sent_count > 0:
            # No response to previous emails
            subject = f"Follow-up: {name} - File #{pv}"
            
            body = f"""Dear Counsel,

I wanted to follow up on my previous correspondence regarding your client {name} (File #{pv}, DOI: {doi}).

We have not yet received a response regarding this matter. The current balance of {balance_str} remains outstanding.

Please advise on the status of this case and when we can expect resolution. If you need any additional documentation or have questions, please let me know.

Thank you for your attention to this matter.

Best regards,"""
        else:
            # General follow-up
            subject = f"Re: {name} - File #{pv}"
            
            body = f"""Dear Counsel,

I'm following up regarding your client {name} (File #{pv}, DOI: {doi}).

Current balance: {balance_str}

Please provide an update on this matter at your earliest convenience.

Thank you.

Best regards,"""
    else:
        # Default follow-up without activity data
        subject = f"Follow-up: {name} - File #{pv}"
        
        body = f"""Dear Counsel,

I am following up regarding your client {name} (File #{pv}, DOI: {doi}).

The current outstanding balance is {balance_str}.

Please provide a status update on this matter. If you need any additional information or documentation, please let me know.

Thank you for your attention to this matter.

Best regards,"""
    
    return {
        'subject': subject,
        'body': body,
        'pv': pv,
        'name': name,
        'balance': balance_str
    }
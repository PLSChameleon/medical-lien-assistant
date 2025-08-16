"""
Status request email template generator
"""

def generate_status_request_email(case_data, case_activity=None):
    """
    Generate a status request email based on case data
    
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
    
    # Generate status request
    subject = f"Status Request: {name} - File #{pv}"
    
    body = f"""Dear Counsel,

I am writing to request a status update on your client {name} (File #{pv}).

Case Details:
- Client: {name}
- File #: {pv}
- Date of Injury: {doi}
- Outstanding Balance: {balance_str}

Please provide the following information:
1. Current status of the case
2. Expected timeline for resolution
3. Any issues or concerns that need to be addressed
4. Whether additional documentation is needed

Your prompt response would be greatly appreciated as we need to update our records.

Thank you for your cooperation.

Best regards,"""
    
    return {
        'subject': subject,
        'body': body,
        'pv': pv,
        'name': name,
        'balance': balance_str
    }
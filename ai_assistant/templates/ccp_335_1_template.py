"""
CCP 335.1 Statute of Limitations Email Template
For cases over 2 years old where litigation status is unknown
"""

CCP_335_1_TEMPLATE = """Subject: {name} {doi} // Prohealth Advanced Imaging - CCP 335.1 Inquiry

Dear Counsel,

As you are aware, Transon represents Prohealth Advanced Imaging regarding the outstanding lien of {name} in the amount of ${amount}, with a DOI of {doi}. 

The two-year statute of limitations (CCP 335.1), which requires that you file a lawsuit on behalf of your client, has passed. Please provide the venue and case number of the action you filed so that I can update our client accordingly. 

If the case settled prior to the CCP 335.1 deadline, please advise of the settlement amount and contact me directly to negotiate the Prohealth lien.

Thank you for your prompt attention to this matter.

Sincerely,
Dean Hunter
Transcon Financial Inc.
Dean@transconsolution.com
(714) 630-6800

---
Reference: PV#{pv} | CMS#{cms}
"""

def get_ccp_335_1_email(case_data):
    """
    Generate CCP 335.1 statute of limitations inquiry email
    
    Args:
        case_data: Dictionary containing case information with keys:
            - name: Patient name
            - doi: Date of injury
            - pv: PV number
            - cms: CMS number
            - amount: Lien amount (optional, will use placeholder if not provided)
    
    Returns:
        Tuple of (subject, body) for the email
    """
    # Extract case information
    name = case_data.get('name', 'UNKNOWN').title()
    doi = case_data.get('doi', 'UNKNOWN')
    pv = case_data.get('pv', 'UNKNOWN')
    cms = case_data.get('cms', 'UNKNOWN')
    
    # Handle lien amount - may need to be looked up or use placeholder
    amount = case_data.get('amount', '[AMOUNT]')
    if not amount or amount == 'nan':
        amount = '[AMOUNT]'
    
    # Format DOI if it's a datetime object
    if hasattr(doi, 'strftime'):
        doi = doi.strftime("%m/%d/%Y")
    elif doi and str(doi) not in ['nan', 'NaT', 'UNKNOWN']:
        # Ensure proper date format
        doi_str = str(doi).split()[0]  # Remove time if present
        doi = doi_str
    else:
        doi = 'UNKNOWN'
    
    # Generate subject
    subject = f"{name} {doi} // Prohealth Advanced Imaging - CCP 335.1 Inquiry"
    
    # Generate body
    body = CCP_335_1_TEMPLATE.format(
        name=name,
        doi=doi,
        pv=pv,
        cms=cms,
        amount=amount
    )
    
    return subject, body

def is_ccp_335_1_eligible(case_data, email_cache_service=None):
    """
    Determine if a case is eligible for CCP 335.1 email
    
    Args:
        case_data: Dictionary containing case information
        email_cache_service: Optional EmailCacheService to check prior communications
    
    Returns:
        Boolean indicating if case needs CCP 335.1 email
    """
    from datetime import datetime, timedelta
    import pandas as pd
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Check if DOI is over 2 years old
    doi_raw = case_data.get('doi')
    if not doi_raw or str(doi_raw) in ['nan', 'NaT', '2099', 'UNKNOWN', '']:
        return False
    
    try:
        # Convert DOI to datetime
        if hasattr(doi_raw, 'year'):
            doi_date = doi_raw
        else:
            doi_str = str(doi_raw).split()[0]
            doi_date = pd.to_datetime(doi_str)
        
        # Check if over 2 years old
        years_old = (datetime.now() - doi_date).days / 365
        if years_old <= 2:
            return False
        
        # If we have email cache, check if we've already received litigation info
        # But be more lenient - only exclude if we have CLEAR litigation status
        if email_cache_service:
            try:
                pv = case_data.get('pv')
                attorney_email = case_data.get('attorney_email')
                
                # Check if we have clear litigation status for this case
                litigation_info = email_cache_service.has_litigation_status(pv, attorney_email)
                if litigation_info.get('has_status'):
                    # Check if the keywords indicate active litigation or settlement
                    details = litigation_info.get('details', {})
                    keywords = details.get('keywords_found', [])
                    
                    # Only exclude if we have definitive keywords indicating litigation status
                    definitive_keywords = ['settled', 'settlement', 'case number', 'venue', 
                                         'trial', 'verdict', 'judgment', 'dismissed',
                                         'litigation', 'pre-litigation', 'prelitigation', 
                                         'prelit', 'pre litigation', 'pre-lit', 'in litigation',
                                         'litigating', 'litigated', 'lawsuit', 'filed']
                    
                    if any(kw in definitive_keywords for kw in keywords):
                        logger.debug(f"Case {pv} excluded from CCP 335.1 - has litigation status: {keywords}")
                        return False
            except Exception as e:
                # If there's an error checking email cache, still allow CCP 335.1
                logger.warning(f"Error checking email cache for CCP 335.1 eligibility: {e}")
                pass
        
        # Case is over 2 years old and we don't have definitive litigation status
        logger.debug(f"Case {case_data.get('pv')} eligible for CCP 335.1 - DOI {years_old:.1f} years old")
        return True
        
    except Exception as e:
        # If we can't parse the date, don't send CCP email
        logger.error(f"Error checking CCP 335.1 eligibility: {e}")
        return False
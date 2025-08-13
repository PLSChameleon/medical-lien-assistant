"""
Quick improvements that can be added to the existing system
These are high-impact, low-effort additions
"""

import pandas as pd
from datetime import datetime, timedelta
import json
import os

class PriorityScoring:
    """Add priority scoring to help collectors focus on best cases"""
    
    def __init__(self):
        # Load or initialize firm response rates
        self.firm_scores_file = "data/firm_intelligence.json"
        self.firm_scores = self.load_firm_scores()
    
    def load_firm_scores(self):
        """Load historical firm performance data"""
        if os.path.exists(self.firm_scores_file):
            with open(self.firm_scores_file, 'r') as f:
                return json.load(f)
        return {}
    
    def calculate_case_priority(self, case):
        """
        Score each case 0-100 based on likelihood of collection
        
        Scoring factors:
        - Firm responsiveness history (0-40 points)
        - Case age sweet spot (0-30 points)
        - Days since last contact (0-20 points)
        - Case value (0-10 points)
        """
        score = 0
        
        # 1. Firm responsiveness (0-40 points)
        firm_email = case.get('Attorney Email', '').lower()
        if firm_email in self.firm_scores:
            firm_data = self.firm_scores[firm_email]
            response_rate = firm_data.get('response_rate', 0.5)
            score += int(response_rate * 40)
        else:
            score += 20  # Default middle score for unknown firms
        
        # 2. Case age sweet spot (0-30 points)
        # Best: 6-18 months old
        doi = case.get('DOI')
        if doi:
            try:
                if hasattr(doi, 'date'):
                    doi_date = doi
                else:
                    doi_date = pd.to_datetime(str(doi))
                
                months_old = (datetime.now() - doi_date).days / 30
                
                if 6 <= months_old <= 18:
                    score += 30  # Perfect age
                elif 3 <= months_old < 6:
                    score += 20  # Good but young
                elif 18 < months_old <= 24:
                    score += 20  # Good but aging
                elif 24 < months_old <= 36:
                    score += 10  # Getting old
                # Too young (<3 months) or too old (>36 months) get 0
                
            except:
                score += 15  # Default for unknown age
        
        # 3. Days since last contact (0-20 points)
        # Prefer cases with recent activity but not too recent
        last_contact = case.get('Last Contact')
        if last_contact:
            try:
                days_since = (datetime.now() - pd.to_datetime(last_contact)).days
                if 20 <= days_since <= 40:
                    score += 20  # Perfect follow-up window
                elif 40 < days_since <= 60:
                    score += 15  # Good follow-up window
                elif 60 < days_since <= 90:
                    score += 10  # Needs attention
                elif days_since > 90:
                    score += 5   # Long overdue
                # Too recent (<20 days) gets 0 - don't pester
            except:
                score += 10  # Default
        else:
            score += 20  # Never contacted - high priority
        
        # 4. Case value (0-10 points) - if available
        billing_amount = case.get('Billing Amount', 0)
        if billing_amount:
            try:
                amount = float(billing_amount)
                if amount >= 10000:
                    score += 10
                elif amount >= 5000:
                    score += 7
                elif amount >= 2500:
                    score += 5
                elif amount >= 1000:
                    score += 3
            except:
                pass
        
        return min(score, 100)  # Cap at 100
    
    def update_firm_score(self, firm_email, responded=False, paid=False):
        """Update firm intelligence based on interactions"""
        firm_email = firm_email.lower()
        
        if firm_email not in self.firm_scores:
            self.firm_scores[firm_email] = {
                'emails_sent': 0,
                'responses': 0,
                'payments': 0,
                'response_rate': 0,
                'payment_rate': 0
            }
        
        firm_data = self.firm_scores[firm_email]
        firm_data['emails_sent'] += 1
        
        if responded:
            firm_data['responses'] += 1
        if paid:
            firm_data['payments'] += 1
        
        # Update rates
        if firm_data['emails_sent'] > 0:
            firm_data['response_rate'] = firm_data['responses'] / firm_data['emails_sent']
            firm_data['payment_rate'] = firm_data['payments'] / firm_data['emails_sent']
        
        # Save updated scores
        with open(self.firm_scores_file, 'w') as f:
            json.dump(self.firm_scores, f, indent=2)
    
    def get_prioritized_cases(self, cases_df, top_n=50):
        """Return top N cases by priority score"""
        # Calculate scores for all cases
        scores = []
        for _, case in cases_df.iterrows():
            case_dict = case.to_dict()
            score = self.calculate_case_priority(case_dict)
            scores.append({
                'PV': case_dict.get('PV', ''),
                'Name': case_dict.get('Name', ''),
                'Score': score,
                'Law Firm': case_dict.get('Law Firm', ''),
                'DOI': case_dict.get('DOI', '')
            })
        
        # Sort by score
        scores.sort(key=lambda x: x['Score'], reverse=True)
        
        return scores[:top_n]


class ResponseTracker:
    """Track email responses and learn patterns"""
    
    def __init__(self):
        self.response_log_file = "data/response_tracking.json"
        self.response_data = self.load_responses()
    
    def load_responses(self):
        """Load response tracking data"""
        if os.path.exists(self.response_log_file):
            with open(self.response_log_file, 'r') as f:
                return json.load(f)
        return {
            'emails': [],
            'patterns': {
                'best_send_day': None,
                'best_send_hour': None,
                'avg_response_time_hours': None
            }
        }
    
    def log_email_sent(self, pv, firm_email, template_type):
        """Log when an email is sent"""
        self.response_data['emails'].append({
            'pv': pv,
            'firm': firm_email,
            'template': template_type,
            'sent_time': datetime.now().isoformat(),
            'sent_day': datetime.now().strftime('%A'),
            'sent_hour': datetime.now().hour,
            'responded': False,
            'response_time': None
        })
        self.save_responses()
    
    def log_response_received(self, pv, firm_email):
        """Log when a response is received"""
        # Find the most recent email to this firm for this PV
        for email in reversed(self.response_data['emails']):
            if email['pv'] == pv and email['firm'] == firm_email and not email['responded']:
                email['responded'] = True
                email['response_time'] = datetime.now().isoformat()
                
                # Calculate response time in hours
                sent_time = datetime.fromisoformat(email['sent_time'])
                response_time = datetime.now()
                hours_to_response = (response_time - sent_time).total_seconds() / 3600
                email['response_hours'] = hours_to_response
                
                break
        
        self.save_responses()
        self.analyze_patterns()
    
    def analyze_patterns(self):
        """Analyze response patterns to find best practices"""
        responded_emails = [e for e in self.response_data['emails'] if e['responded']]
        
        if not responded_emails:
            return
        
        # Best day analysis
        day_responses = {}
        for email in responded_emails:
            day = email['sent_day']
            if day not in day_responses:
                day_responses[day] = []
            day_responses[day].append(email.get('response_hours', 0))
        
        # Find day with best response rate
        best_day = min(day_responses.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else float('inf'))
        self.response_data['patterns']['best_send_day'] = best_day[0]
        
        # Best hour analysis
        hour_responses = {}
        for email in responded_emails:
            hour = email['sent_hour']
            if hour not in hour_responses:
                hour_responses[hour] = []
            hour_responses[hour].append(email.get('response_hours', 0))
        
        # Find hour with best response rate
        if hour_responses:
            best_hour = min(hour_responses.items(), key=lambda x: sum(x[1])/len(x[1]) if x[1] else float('inf'))
            self.response_data['patterns']['best_send_hour'] = best_hour[0]
        
        # Average response time
        response_times = [e['response_hours'] for e in responded_emails if 'response_hours' in e]
        if response_times:
            self.response_data['patterns']['avg_response_time_hours'] = sum(response_times) / len(response_times)
        
        self.save_responses()
    
    def save_responses(self):
        """Save response data to file"""
        os.makedirs(os.path.dirname(self.response_log_file), exist_ok=True)
        with open(self.response_log_file, 'w') as f:
            json.dump(self.response_data, f, indent=2)
    
    def get_firm_stats(self, firm_email):
        """Get response statistics for a specific firm"""
        firm_emails = [e for e in self.response_data['emails'] if e['firm'] == firm_email]
        
        if not firm_emails:
            return None
        
        responded = [e for e in firm_emails if e['responded']]
        response_rate = len(responded) / len(firm_emails) if firm_emails else 0
        
        avg_response_time = None
        if responded:
            response_times = [e['response_hours'] for e in responded if 'response_hours' in e]
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
        
        return {
            'total_emails': len(firm_emails),
            'responses': len(responded),
            'response_rate': f"{response_rate*100:.1f}%",
            'avg_response_time_hours': avg_response_time
        }


class SmartBatchCreator:
    """Create intelligent batches for processing"""
    
    @staticmethod
    def create_smart_batches(cases_df, priority_scorer):
        """Create batches organized by priority and firm"""
        
        batches = {
            'urgent_high_value': [],
            'responsive_firms': [],
            'follow_up_needed': [],
            'new_contacts': [],
            'by_firm': {}
        }
        
        # Calculate priorities
        for _, case in cases_df.iterrows():
            case_dict = case.to_dict()
            score = priority_scorer.calculate_case_priority(case_dict)
            case_dict['priority_score'] = score
            
            # Categorize
            if score >= 80:
                batches['urgent_high_value'].append(case_dict)
            elif score >= 60:
                batches['responsive_firms'].append(case_dict)
            elif score >= 40:
                batches['follow_up_needed'].append(case_dict)
            else:
                batches['new_contacts'].append(case_dict)
            
            # Also group by firm
            firm = case_dict.get('Law Firm', 'Unknown')
            if firm not in batches['by_firm']:
                batches['by_firm'][firm] = []
            batches['by_firm'][firm].append(case_dict)
        
        return batches


# Example usage integration with existing system:
def enhance_bulk_email_service():
    """
    Add these enhancements to your existing BulkEmailService
    """
    
    # Initialize enhancers
    priority_scorer = PriorityScoring()
    response_tracker = ResponseTracker()
    
    # When categorizing cases, add priority scores
    def enhanced_categorize_cases(self, df):
        # Get original categories
        categories = self.original_categorize_cases(df)
        
        # Add priority-based categories
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for _, row in df.iterrows():
            case = row.to_dict()
            score = priority_scorer.calculate_case_priority(case)
            
            if score >= 70:
                high_priority.append(case)
            elif score >= 40:
                medium_priority.append(case)
            else:
                low_priority.append(case)
        
        categories['high_priority'] = high_priority
        categories['medium_priority'] = medium_priority
        categories['low_priority'] = low_priority
        
        return categories
    
    # When sending emails, track them
    def enhanced_send_email(self, email_data):
        # Send email as normal
        result = self.original_send_email(email_data)
        
        # Track the send
        response_tracker.log_email_sent(
            email_data['pv'],
            email_data['to'],
            email_data.get('template_type', 'standard')
        )
        
        return result
    
    # Show priority scores in batch preview
    def enhanced_display_batch(self, emails):
        print("\n📊 Batch Preview (with Priority Scores):")
        for email in emails[:10]:
            case = email.get('case_data', {})
            score = priority_scorer.calculate_case_priority(case)
            
            priority_label = "🔥 HIGH" if score >= 70 else "⚡ MED" if score >= 40 else "📋 LOW"
            
            print(f"[{priority_label}] PV: {email['pv']} - Score: {score}")
            print(f"    To: {email['to']}")
            print(f"    Name: {email['name']}")
            print()
    
    return priority_scorer, response_tracker


if __name__ == "__main__":
    # Quick test of priority scoring
    print("Testing Priority Scoring System...")
    
    scorer = PriorityScoring()
    
    # Test case
    test_case = {
        'PV': '12345',
        'Name': 'John Doe',
        'DOI': datetime.now() - timedelta(days=300),  # 10 months old
        'Attorney Email': 'test@lawfirm.com',
        'Last Contact': datetime.now() - timedelta(days=35),  # 35 days ago
        'Billing Amount': 5500
    }
    
    score = scorer.calculate_case_priority(test_case)
    print(f"Test case priority score: {score}/100")
    
    # Test response tracking
    tracker = ResponseTracker()
    tracker.log_email_sent('12345', 'test@lawfirm.com', 'follow_up')
    print("Email send logged successfully")
    
    print("\n✅ Enhancement modules ready to integrate!")
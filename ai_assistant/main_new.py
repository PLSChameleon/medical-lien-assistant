#!/usr/bin/env python3
"""
Prohealth Medical Lien Automation Assistant
Main application entry point
"""

import os
import sys
import logging
from datetime import datetime

# Fix Windows UTF-8 encoding issues
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from config import Config
from utils.logging_config import setup_logging, log_sent_email
from services.gmail_service import GmailService
from services.ai_service import AIService
from services.email_cache_service import EmailCacheService
from services.collections_tracker import CollectionsTracker
try:
    from services.collections_tracker_enhanced import EnhancedCollectionsTracker
except ImportError:
    EnhancedCollectionsTracker = None
from services.cms_integration import add_cms_note_for_email
from services.bulk_email_service import BulkEmailService
from case_manager import CaseManager

logger = logging.getLogger(__name__)

class AssistantApp:
    """Main application class"""
    
    def __init__(self):
        self.gmail_service = None
        self.ai_service = None
        self.case_manager = None
        self.email_cache_service = None
        self.collections_tracker = None
        self.bulk_email_service = None
        self._initialize_services()
    
    def _build_search_query(self, case):
        """Build consistent Gmail search query for a case"""
        query = f'"{case["Name"]}" OR {case["PV"]}'
        if case.get('CMS'):
            query += f' OR {case["CMS"]}'
        # Note: DOI (Date of Injury) excluded as Gmail can't search datetime objects properly
        return query
    
    def _suggest_next_actions(self, case, email_messages):
        """Suggest next actions to user after case summary"""
        try:
            print("\n" + "="*50)
            print("💡 SUGGESTED NEXT ACTIONS")
            print("="*50)
            
            # Analyze email recency and content to suggest actions
            if not email_messages:
                print("📝 No emails found - consider sending initial status request")
                return
            
            # Check for recent activity (last 30 days)
            from datetime import datetime, timedelta
            import pytz
            
            # Create timezone-aware cutoff date
            recent_cutoff = datetime.now(pytz.UTC) - timedelta(days=30)
            recent_emails = [msg for msg in email_messages if self._parse_email_date(msg.get('date', '')) > recent_cutoff]
            
            if recent_emails:
                print(f"📬 Recent activity found ({len(recent_emails)} emails in last 30 days)")
                print("   Recommended: Wait or send gentle follow-up")
            else:
                print(f"⏰ No recent activity ({len(email_messages)} total emails found)")
                print("   Recommended: Send follow-up to check case status")
            
            # Extract potential new contacts
            new_contacts = self._extract_email_addresses(email_messages)
            if new_contacts:
                print(f"\n📧 New contacts found in emails:")
                for contact in new_contacts[:3]:  # Show up to 3
                    print(f"   • {contact}")
            
            # Interactive options
            print("\nWhat would you like to do?")
            print("1. Draft follow-up email")
            print("2. Draft status request email") 
            print("3. Show email threads for selection")
            print("4. Extract all email addresses from conversations")
            print("5. Continue with next case")
            
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == "1":
                self.draft_followup_email(case)
            elif choice == "2":
                self.draft_status_request(case)
            elif choice == "3":
                self._show_thread_selection(case, email_messages)
            elif choice == "4":
                self._show_all_extracted_emails(email_messages)
            elif choice == "5":
                print("✅ Continuing...")
            else:
                print("Invalid choice. Continuing...")
                
        except Exception as e:
            logger.error(f"Error in next actions suggestion: {e}")
            print("❌ Error suggesting next actions")
    
    def _parse_email_date(self, date_string):
        """Parse email date string to datetime object (timezone-aware)"""
        try:
            from email.utils import parsedate_to_datetime
            import pytz
            
            parsed_date = parsedate_to_datetime(date_string)
            
            # If the parsed date is naive (no timezone), make it UTC
            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(tzinfo=pytz.UTC)
            
            return parsed_date
        except:
            # Return a very old timezone-aware date if parsing fails
            import pytz
            return datetime(1970, 1, 1, tzinfo=pytz.UTC)
    
    def _extract_email_addresses(self, email_messages):
        """Extract email addresses from email content"""
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found_emails = set()
        
        for msg in email_messages:
            # Check in sender/recipient fields
            for field in ['from', 'to']:
                if msg.get(field):
                    emails = re.findall(email_pattern, msg[field])
                    found_emails.update(emails)
            
            # Check in snippet/content
            if msg.get('snippet'):
                emails = re.findall(email_pattern, msg['snippet'])
                found_emails.update(emails)
        
        # Filter out common addresses and the case's known attorney email
        excluded = {'noreply', 'no-reply', 'donotreply', 'support', 'info'}
        attorney_email = self.current_case.get('Attorney Email', '').lower() if hasattr(self, 'current_case') else ''
        
        filtered_emails = [
            email for email in found_emails 
            if not any(exclude in email.lower() for exclude in excluded)
            and email.lower() != attorney_email
        ]
        
        return list(filtered_emails)
    
    def _show_thread_selection(self, case, email_messages):
        """Show available email threads for user selection"""
        print("\n📧 Available Email Threads:")
        print("-" * 50)
        
        for i, msg in enumerate(email_messages, 1):
            print(f"{i}. From: {msg.get('from', 'Unknown')}")
            print(f"   Subject: {msg.get('subject', 'No Subject')}")
            print(f"   Date: {msg.get('date', 'Unknown')}")
            print(f"   Snippet: {msg.get('snippet', '')[:100]}...")
            print()
        
        try:
            choice = input(f"Select thread to reply to (1-{len(email_messages)}): ").strip()
            thread_num = int(choice) - 1
            
            if 0 <= thread_num < len(email_messages):
                selected_msg = email_messages[thread_num]
                print(f"✅ Selected thread from {selected_msg.get('from')}")
                # Here you could implement thread-specific follow-up logic
                self.draft_followup_email(case)
            else:
                print("❌ Invalid selection")
        except ValueError:
            print("❌ Invalid input")
    
    def _show_all_extracted_emails(self, email_messages):
        """Show all extracted email addresses from conversations"""
        emails = self._extract_email_addresses(email_messages)
        
        print("\n📧 All Email Addresses Found:")
        print("-" * 50)
        
        if not emails:
            print("No additional email addresses found in conversations.")
            return
        
        for i, email in enumerate(emails, 1):
            print(f"{i}. {email}")
        
        print(f"\n✅ Found {len(emails)} email addresses")
        print("💡 Consider adding relevant contacts to your case records")
    
    def _check_onboarding(self):
        """Check if user needs onboarding (first-time setup)"""
        try:
            if self.email_cache_service.is_cache_stale(max_age_days=30):
                print("\n" + "="*60)
                print("🎉 WELCOME TO PROHEALTH AI ASSISTANT!")
                print("="*60)
                print("\n🔧 First-time setup detected. Let's get you started!")
                
                print("\nThis assistant will help you:")
                print("• Summarize case emails and suggest next actions")
                print("• Draft professional follow-up emails")
                print("• Extract contact information from conversations")
                print("• Maintain consistent communication style")
                
                setup_choice = input("\n🚀 Would you like to run initial setup? (recommended for new users) [y/n]: ").strip().lower()
                
                if setup_choice == 'y':
                    self._run_onboarding()
        except Exception as e:
            logger.error(f"Error in onboarding check: {e}")
    
    def _run_onboarding(self):
        """Run first-time user onboarding"""
        try:
            print("\n📥 STEP 1: Email Cache Setup")
            print("To provide personalized email suggestions, we'll analyze your recent sent emails.")
            print("This helps maintain your writing style and tone consistency.")
            
            cache_choice = input("\n📧 Download and analyze your last 500 sent emails? [y/n]: ").strip().lower()
            
            if cache_choice == 'y':
                self.email_cache_service.download_sent_emails(500)
                print("✅ Email analysis complete! Your writing style has been analyzed.")
            else:
                print("⏭️ Skipping email analysis - default professional style will be used.")
            
            print("\n🎯 STEP 2: Quick Tutorial")
            print("Here are the main commands you'll use:")
            print("• 'summarize pv 12345' - Get case summary and suggestions")
            print("• 'draft follow-up for 12345' - Create follow-up emails")
            print("• 'draft status request for 12345' - Send new status requests")
            
            print("\n💡 Pro Tips:")
            print("• After each summary, you'll get interactive suggestions")
            print("• The system extracts new email contacts automatically")
            print("• Your emails will match your established writing style")
            
            input("\nPress Enter to continue to the main application...")
            
        except Exception as e:
            logger.error(f"Error in onboarding: {e}")
            print(f"❌ Onboarding error: {e}")
    
    def _show_collections_dashboard(self):
        """Display collections performance dashboard"""
        try:
            dashboard = self.collections_tracker.get_collections_dashboard()
            
            print("\n" + "="*60)
            print("📊 COLLECTIONS PERFORMANCE DASHBOARD")
            print("="*60)
            
            print(f"\n📈 Overview:")
            print(f"   Total tracked cases: {dashboard['total_cases']}")
            
            if dashboard['status_breakdown']:
                print(f"\n📋 Case Status Breakdown:")
                for status, count in dashboard['status_breakdown'].items():
                    print(f"   {status.title()}: {count}")
            
            stale = dashboard['stale_cases']
            print(f"\n⏰ Case Aging Analysis:")
            print(f"   30+ days old: {stale['30_days']} cases")
            print(f"   60+ days old: {stale['60_days']} cases")
            print(f"   90+ days old: {stale['90_days']} cases")
            
            if dashboard['top_responsive_firms']:
                print(f"\n🏆 Top Responsive Law Firms:")
                for firm, rate in dashboard['top_responsive_firms']:
                    print(f"   {firm}: {rate:.1f}% response rate")
            
            print("\n💡 Use 'stale cases' to see which cases need follow-up")
            
        except Exception as e:
            logger.error(f"Error showing collections dashboard: {e}")
            print(f"❌ Error showing dashboard: {e}")
    
    def _show_stale_cases(self):
        """Show cases that need follow-up"""
        try:
            stale_cases = self.collections_tracker.get_stale_cases(days_threshold=30)
            
            print("\n" + "="*60)
            print("⏰ STALE CASES NEEDING FOLLOW-UP")
            print("="*60)
            
            if not stale_cases:
                print("\n🎉 No stale cases found! All cases are up to date.")
                return
            
            print(f"\nFound {len(stale_cases)} cases needing follow-up:")
            print("-" * 60)
            
            for i, case in enumerate(stale_cases[:10], 1):  # Show top 10
                print(f"{i}. PV {case['pv']}")
                print(f"   Last contact: {case['days_since_contact']} days ago")
                print(f"   Status: {case['status'].title()}")
                if case['firm_email']:
                    print(f"   Firm: {case['firm_email']}")
                print()
            
            if len(stale_cases) > 10:
                print(f"... and {len(stale_cases) - 10} more cases")
            
            print("\n💡 Use 'summarize pv <number>' to review and follow up on these cases")
            
        except Exception as e:
            logger.error(f"Error showing stale cases: {e}")
            print(f"❌ Error showing stale cases: {e}")
    
    def _show_comprehensive_stale_cases(self):
        """Show comprehensive stale case analysis with categories"""
        try:
            stale_categories = self.collections_tracker.get_comprehensive_stale_cases(self.case_manager)
            
            print("\n" + "="*60)
            print("⏰ COMPREHENSIVE STALE CASE ANALYSIS")
            print("="*60)
            
            total_stale = sum(len(cases) for cases in stale_categories.values())
            if total_stale == 0:
                print("\n🎉 No stale cases found! All cases are up to date.")
                print("\n💡 Tip: Run 'bootstrap collections' to populate with historical email data")
                return
            
            # Show each category
            for category, cases in stale_categories.items():
                if not cases:
                    continue
                    
                category_name = category.replace("_", " ").title()
                print(f"\n🔥 {category_name} ({len(cases)} cases):")
                print("-" * 50)
                
                for i, case in enumerate(cases[:5], 1):  # Show top 5 per category
                    print(f"{i}. PV {case['pv']} - {case['name']}")
                    if case['days_since_contact']:
                        print(f"   📅 Last contact: {case['days_since_contact']} days ago")
                    else:
                        print(f"   📅 No recorded contact")
                    print(f"   📧 Law Firm: {case['law_firm']}")
                    print(f"   🏛️  Attorney: {case['attorney_email']}")
                    print()
                
                if len(cases) > 5:
                    print(f"   ... and {len(cases) - 5} more cases in this category")
                    print()
            
            # Priority recommendations
            high_priority_count = len(stale_categories["high_priority"])
            no_contact_count = len(stale_categories["no_contact"])
            
            print("\n💡 RECOMMENDED ACTIONS:")
            if high_priority_count > 0:
                print(f"🚨 URGENT: {high_priority_count} cases need immediate attention (60+ days)")
            if no_contact_count > 0:
                print(f"📞 START: {no_contact_count} cases have never been contacted")
                
            print(f"\n📊 Total stale cases: {total_stale}")
            print("Use 'summarize pv <number>' to review specific cases")
            
            # Show interactive menu for quick category access
            self._show_stale_cases_menu(stale_categories)
            
        except Exception as e:
            logger.error(f"Error showing comprehensive stale cases: {e}")
            print(f"❌ Error showing stale cases: {e}")
    
    def _show_stale_cases_menu(self, stale_categories):
        """Show interactive menu for quick category access after stale cases analysis"""
        try:
            # Count cases in each category
            critical_count = len(stale_categories.get("critical", []))
            high_priority_count = len(stale_categories.get("high_priority", []))
            needs_followup_count = len(stale_categories.get("needs_follow_up", []))
            never_contacted_count = len(stale_categories.get("never_contacted", []))
            no_response_count = len(stale_categories.get("no_response", []))
            unresponsive_firms_count = len(stale_categories.get("unresponsive_firms", []))
            missing_bootstrap_count = len(stale_categories.get("missing_from_bootstrap", []))
            
            total_count = critical_count + high_priority_count + needs_followup_count + never_contacted_count + no_response_count + unresponsive_firms_count + missing_bootstrap_count
            
            if total_count == 0:
                return  # No menu needed if no stale cases
            
            print("\n" + "="*60)
            print("🎯 QUICK CATEGORY ACCESS")
            print("="*60)
            print("\nSelect a category to work with:")
            
            options = []
            option_num = 1
            if critical_count > 0:
                options.append((option_num, f"Critical cases (90+ days) - {critical_count} cases", "critical"))
                option_num += 1
            if high_priority_count > 0:
                options.append((option_num, f"High priority cases (60+ days) - {high_priority_count} cases", "high_priority"))
                option_num += 1
            if needs_followup_count > 0:
                options.append((option_num, f"Follow-up required (30+ days) - {needs_followup_count} cases", "needs_follow_up"))
                option_num += 1
            if never_contacted_count > 0:
                options.append((option_num, f"Never contacted - {never_contacted_count} cases", "never_contacted"))
                option_num += 1
            if no_response_count > 0:
                options.append((option_num, f"No response (emails sent, no replies) - {no_response_count} cases", "no_response"))
                option_num += 1
            if unresponsive_firms_count > 0:
                options.append((option_num, f"Unresponsive firms (multiple contacts, no response) - {unresponsive_firms_count} cases", "unresponsive_firms"))
                option_num += 1
            if missing_bootstrap_count > 0:
                options.append((option_num, f"Missing from bootstrap (need backfill) - {missing_bootstrap_count} cases", "missing_from_bootstrap"))
                option_num += 1
            
            # Display numbered options
            for num, description, _ in options:
                print(f"{num}. {description}")
            
            print(f"{option_num}. Skip menu and continue")
            
            # Get user choice
            choice = input(f"\nEnter your choice (1-{option_num}): ").strip()
            
            # Process choice
            selected_category = None
            for num, description, category in options:
                if choice == str(num):
                    selected_category = category
                    break
            
            if choice == str(option_num):
                print("✅ Continuing...")
                return
            elif selected_category:
                self._show_category_details(selected_category, stale_categories)
            else:
                print("❌ Invalid choice. Continuing...")
                
        except Exception as e:
            logger.error(f"Error showing stale cases menu: {e}")
            print(f"❌ Error showing menu: {e}")
    
    def _show_category_details(self, category, stale_categories):
        """Show detailed view of a specific stale case category"""
        try:
            cases = stale_categories.get(category, [])
            if not cases:
                print(f"❌ No cases found in {category} category")
                return
            
            # Category display names
            category_names = {
                "critical": "🚨 CRITICAL CASES (90+ days)",
                "high_priority": "🔥 HIGH PRIORITY CASES (60+ days)",
                "needs_follow_up": "📋 FOLLOW-UP REQUIRED (30+ days)",
                "never_contacted": "📝 NEVER CONTACTED",
                "no_response": "📧 NO RESPONSE (Emails sent, no replies)",
                "unresponsive_firms": "🔇 UNRESPONSIVE FIRMS (Multiple contacts, no response)",
                "missing_from_bootstrap": "❓ MISSING FROM BOOTSTRAP (Need backfill)"
            }
            
            category_title = category_names.get(category, category.title())
            
            print(f"\n{category_title}")
            print("="*60)
            print(f"Showing 10 of {len(cases)} cases (use 'list {category.replace('_', '-')}' for more details)")
            print("-" * 50)
            
            # Show first 10 cases with summary info
            display_cases = cases[:10]
            for i, case in enumerate(display_cases, 1):
                print(f"{i}. PV {case['pv']} - {case['name']}")
                if case.get('days_since_contact'):
                    print(f"   📅 {case['days_since_contact']} days since last contact")
                else:
                    print(f"   📅 No recorded contact")
                print(f"   🏛️  {case.get('law_firm', 'Unknown Firm')}")
                print(f"   📧 {case.get('attorney_email', 'No email')}")
                print()
            
            if len(cases) > 10:
                print(f"... and {len(cases) - 10} more cases in this category")
            
            # Ask if user wants to work on a case
            print(f"\n💡 QUICK ACTIONS:")
            print(f"Enter PV number to review a case, or 'continue' to go back:")
            
            choice = input("> ").strip()
            
            if choice.lower() == 'continue':
                return
            elif choice.isdigit():
                # Check if PV is in our displayed cases
                case_pvs = [case['pv'] for case in display_cases]
                if choice in case_pvs:
                    case = self.case_manager.get_case_by_pv(choice)
                    if case:
                        self.summarize_case(case)
                else:
                    print(f"❌ PV {choice} not found in displayed cases")
            else:
                print("❌ Invalid input")
                
        except Exception as e:
            logger.error(f"Error showing category details: {e}")
            print(f"❌ Error showing category details: {e}")
    
    def _bootstrap_collections_tracker(self):
        """Bootstrap the collections tracker with historical email data"""
        try:
            print("\n📥 Bootstrapping Collections Tracker")
            print("="*50)
            print("This will analyze your entire Gmail history to populate case tracking data...")
            print("🔍 This searches your full Gmail account (not just the 500 email cache)")
            print("⚠️  This process may take several minutes to complete.")
            
            # Get user confirmation
            confirm = input("\nProceed with comprehensive Gmail bootstrap analysis? (y/n): ").strip().lower()
            if confirm != 'y':
                print("Bootstrap cancelled.")
                return
            
            # Run the bootstrap using Gmail direct search
            print("\n🔍 Searching your entire Gmail history for collections activities...")
            results = self.collections_tracker.bootstrap_from_gmail_direct(
                self.gmail_service,
                self.case_manager
            )
            
            if results:
                print(f"\n✅ Bootstrap Complete!")
                print(f"📊 Results:")
                print(f"   • Processed {results['processed_cases']} active cases")
                print(f"   • Found {results['matched_activities']} collections-related activities")
                print(f"   • Now tracking {results['cases_tracked']} cases with historical data")
                
                print(f"\n💡 You can now use 'stale cases' to see comprehensive analysis!")
                
                # Show quick preview
                preview_choice = input("\nShow stale cases preview now? (y/n): ").strip().lower()
                if preview_choice == 'y':
                    self._show_comprehensive_stale_cases()
                    
            else:
                print("❌ Bootstrap failed or found no matching data")
            
        except Exception as e:
            logger.error(f"Error bootstrapping collections tracker: {e}")
            print(f"❌ Error during bootstrap: {e}")
    
    def _show_stale_cases_from_gmail(self):
        """Show stale cases by searching Gmail directly for each case"""
        try:
            print("\n" + "="*60)
            print("⏰ ANALYZING ALL CASES FROM GMAIL")
            print("="*60)
            print("🔍 Searching Gmail for activity on all active cases...")
            print("   This analyzes your entire Gmail history (not just the 500 cache)")
            print("   Please wait - this may take a few minutes...\n")
            
            # Get all active cases
            cases_df = self.case_manager.df
            all_cases = []
            
            for _, row in cases_df.iterrows():
                case_info = self.case_manager.format_case(row)
                pv = str(case_info.get("PV", "")).strip()
                status = str(case_info.get("Status", "")).lower()
                
                # Analyze all cases regardless of status
                if pv:
                    all_cases.append({
                        "PV": pv,
                        "Name": case_info.get("Name", ""),
                        "Attorney Email": case_info.get("Attorney Email", ""),
                        "Law Firm": case_info.get("Law Firm", ""),
                        "CMS": case_info.get("CMS", ""),
                        "DOI": case_info.get("DOI", "")
                    })
            
            print(f"📋 Found {len(all_cases)} cases to analyze\n")
            
            # Categories for stale cases
            stale_categories = {
                "critical": [],        # 90+ days no contact
                "high_priority": [],   # 60+ days no contact  
                "needs_follow_up": [], # 30+ days no contact
                "never_contacted": []  # No emails found
            }
            
            # Process cases in batches for progress updates
            batch_size = 50
            total_batches = (len(all_cases) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(all_cases))
                batch = all_cases[start_idx:end_idx]
                
                print(f"📊 Processing batch {batch_num + 1}/{total_batches} (cases {start_idx + 1}-{end_idx})")
                
                for case in batch:
                    try:
                        # Search Gmail for this specific case
                        query = self._build_search_query(case)
                        email_messages = self.gmail_service.search_messages(query, max_results=3)
                        
                        # Find most recent email date
                        last_contact_date = None
                        if email_messages:
                            dates = []
                            for msg in email_messages:
                                try:
                                    msg_date = self._parse_email_date(msg.get('date', ''))
                                    dates.append(msg_date)
                                except:
                                    continue
                            
                            if dates:
                                last_contact_date = max(dates)
                        
                        # Calculate days since last contact
                        days_since_contact = None
                        if last_contact_date:
                            import pytz
                            if last_contact_date.tzinfo is None:
                                last_contact_date = last_contact_date.replace(tzinfo=pytz.UTC)
                            
                            now = datetime.now(pytz.UTC)
                            days_since_contact = (now - last_contact_date).days
                        
                        # Create case data with staleness info
                        case_data = {
                            **case,
                            "days_since_contact": days_since_contact,
                            "last_contact_date": last_contact_date.strftime("%Y-%m-%d") if last_contact_date else None,
                            "email_count": len(email_messages) if email_messages else 0
                        }
                        
                        # Categorize by staleness (collections-specific thresholds)
                        if not email_messages:
                            stale_categories["never_contacted"].append(case_data)
                        elif days_since_contact and days_since_contact >= 90:
                            stale_categories["critical"].append(case_data)
                        elif days_since_contact and days_since_contact >= 60:
                            stale_categories["high_priority"].append(case_data)
                        elif days_since_contact and days_since_contact >= 30:
                            stale_categories["needs_follow_up"].append(case_data)
                        
                    except Exception as e:
                        logger.error(f"Error analyzing case {case['PV']}: {e}")
                        continue
                
                # Brief pause to avoid hitting Gmail API limits too hard
                import time
                time.sleep(0.5)
            
            print("\n✅ Gmail analysis complete!\n")
            
            # Display results by priority
            self._display_stale_case_results(stale_categories)
            
        except Exception as e:
            logger.error(f"Error analyzing stale cases from Gmail: {e}")
            print(f"❌ Error analyzing stale cases: {e}")
    
    def _display_stale_case_results(self, stale_categories):
        """Display the stale case analysis results"""
        
        # Calculate totals
        total_stale = sum(len(cases) for cases in stale_categories.values())
        
        if total_stale == 0:
            print("🎉 AMAZING! No stale cases found!")
            print("All your active cases have been contacted within the last 30 days.\n")
            return
        
        # Display each category with collections-appropriate messaging
        if stale_categories["critical"]:
            cases = stale_categories["critical"]
            print(f"🚨 CRITICAL ATTENTION NEEDED ({len(cases)} cases - 90+ days)")
            print("="*60)
            print("These cases risk being forgotten. Immediate action required!")
            for i, case in enumerate(cases[:10], 1):
                print(f"{i}. PV {case['PV']} - {case['Name']}")
                print(f"   ⏰ Last contact: {case['days_since_contact']} days ago ({case['last_contact_date']})")
                print(f"   🏛️  Firm: {case['Law Firm']}")
                print(f"   📧 Email: {case['Attorney Email']}")
                print()
            if len(cases) > 10:
                print(f"   ... and {len(cases) - 10} more critical cases\n")
        
        if stale_categories["high_priority"]:
            cases = stale_categories["high_priority"]
            print(f"🔥 HIGH PRIORITY ({len(cases)} cases - 60+ days)")
            print("="*60)
            print("These cases need follow-up soon to maintain momentum.")
            for i, case in enumerate(cases[:10], 1):
                print(f"{i}. PV {case['PV']} - {case['Name']}")
                print(f"   ⏰ Last contact: {case['days_since_contact']} days ago ({case['last_contact_date']})")
                print(f"   🏛️  Firm: {case['Law Firm']}")
                print()
            if len(cases) > 10:
                print(f"   ... and {len(cases) - 10} more high priority cases\n")
        
        if stale_categories["needs_follow_up"]:
            cases = stale_categories["needs_follow_up"]
            print(f"📋 NEEDS FOLLOW-UP ({len(cases)} cases - 30+ days)")
            print("="*60)
            print("Standard follow-up timeframe reached.")
            for i, case in enumerate(cases[:5], 1):
                print(f"{i}. PV {case['PV']} - {case['Name']}")
                print(f"   ⏰ Last contact: {case['days_since_contact']} days ago")
                print(f"   🏛️  Firm: {case['Law Firm']}")
                print()
            if len(cases) > 5:
                print(f"   ... and {len(cases) - 5} more cases needing follow-up\n")
        
        if stale_categories["never_contacted"]:
            cases = stale_categories["never_contacted"]
            print(f"📝 NEVER CONTACTED ({len(cases)} cases)")
            print("="*60)
            print("These cases have no Gmail activity - may need initial contact.")
            for i, case in enumerate(cases[:5], 1):
                print(f"{i}. PV {case['PV']} - {case['Name']}")
                print(f"   🏛️  Firm: {case['Law Firm']}")
                print(f"   📧 Email: {case['Attorney Email']}")
                print()
            if len(cases) > 5:
                print(f"   ... and {len(cases) - 5} more uncontacted cases\n")
        
        # Summary and recommendations
        print("📊 SUMMARY & RECOMMENDATIONS")
        print("="*60)
        print(f"Total stale cases: {total_stale}")
        
        # Priority recommendations
        critical_count = len(stale_categories["critical"])
        high_priority_count = len(stale_categories["high_priority"])
        never_contacted_count = len(stale_categories["never_contacted"])
        
        print("\n💡 RECOMMENDED ACTION PLAN:")
        if critical_count > 0:
            print(f"1. 🚨 URGENT: Address {critical_count} critical cases (90+ days) immediately")
        if high_priority_count > 0:
            print(f"2. 🔥 Priority: Follow up on {high_priority_count} high priority cases (60+ days)")
        if never_contacted_count > 0:
            print(f"3. 📞 Initial: Send first contact to {never_contacted_count} uncontacted cases")
        
        print(f"\n💡 Use 'summarize pv <number>' to review specific cases")
        print(f"💡 Use 'draft follow-up for <pv>' to create follow-up emails")
    
    def _initialize_services(self):
        """Initialize all services with proper error handling"""
        try:
            # Validate configuration
            Config.validate_required_vars()
            
            # Initialize services
            self.case_manager = CaseManager()
            self.gmail_service = GmailService()
            self.ai_service = AIService()
            self.email_cache_service = EmailCacheService(self.gmail_service)
            self.collections_tracker = CollectionsTracker()
            # Initialize enhanced tracker if available
            self.enhanced_tracker = None
            if EnhancedCollectionsTracker and hasattr(self, 'email_cache_service'):
                try:
                    self.enhanced_tracker = EnhancedCollectionsTracker(self.email_cache_service)
                    logger.info("Enhanced collections tracker initialized")
                except Exception as e:
                    logger.warning(f"Could not initialize enhanced tracker: {e}")
            
            # Initialize bulk email service
            self.bulk_email_service = BulkEmailService(
                self.gmail_service,
                self.case_manager,
                self.ai_service,
                self.collections_tracker
            )
            
            # Check if this is first run and needs onboarding
            self._check_onboarding()
            
            logger.info("✅ Services initialized successfully")
        
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            raise
    
    async def initialize_cms_session(self):
        """Initialize persistent CMS browser session for automatic note adding"""
        try:
            from services.cms_integration import CMSIntegrationService
            
            logger.info("🔧 Initializing CMS integration...")
            success = await CMSIntegrationService.initialize_persistent_session()
            
            if success:
                logger.info("✅ CMS browser session ready for automatic note adding!")
            else:
                logger.warning("⚠️ CMS session initialization failed - notes will require manual intervention")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ CMS session initialization error: {e}")
            return False
    
    def summarize_case(self, case):
        """Generate case summary with email analysis"""
        try:
            print("\n📄 Case Summary:")
            print(f"Patient: {case['Name']}")
            print(f"PV #: {case['PV']} | CMS: {case['CMS']}")
            print(f"Date of Injury: {case['DOI']}")
            print(f"Attorney Email: {case['Attorney Email']}")
            print(f"Law Firm: {case['Law Firm']}")
            
            # Search for related emails - USE CACHE FIRST
            print("\n🔍 Searching for related emails in cache...")
            query = self._build_search_query(case)
            logger.debug(f"Search query: {query}")
            
            # Try to get emails from cache first
            email_messages = None
            if hasattr(self, 'email_cache_service') and self.email_cache_service:
                # Build search terms for cache lookup
                search_terms = f"{case.get('Name', '')} {case.get('PV', '')} {case.get('CMS', '')}"
                email_messages = self.email_cache_service.get_all_emails_for_case(search_terms)
                if email_messages:
                    print(f"📬 Found {len(email_messages)} related emails in cache")
                else:
                    print("⚠️ No emails found in cache, checking Gmail directly...")
            
            # Fall back to Gmail API if cache is empty or not available
            if not email_messages:
                email_messages = self.gmail_service.search_messages(query)
                if email_messages:
                    print(f"📬 Found {len(email_messages)} related emails from Gmail")
            
            if not email_messages:
                print("❌ No emails found for this case.")
                return
            
            # Generate AI summary
            print("\n🧠 Generating AI summary...")
            summary = self.ai_service.summarize_case_emails(case, email_messages)
            print("\n📄 Summary:")
            print(summary)
            
            # Interactive suggestions after summary
            self._suggest_next_actions(case, email_messages)
            
        except Exception as e:
            logger.error(f"Error summarizing case: {e}")
            print(f"❌ Error generating summary: {e}")
    
    def _show_stale_category(self, category):
        """Show specific stale case category quickly"""
        try:
            # Map user-friendly names to internal categories
            category_map = {
                "critical": "critical",
                "high-priority": "high_priority", 
                "needs-followup": "needs_follow_up",
                "no-contact": "no_contact",
                "no-response": "no_response",
                "unresponsive": "unresponsive_firms",
                "missing": "missing_from_bootstrap"
            }
            
            internal_category = category_map.get(category)
            if not internal_category:
                print(f"❌ Unknown category: {category}")
                print("Available categories: critical, high-priority, needs-followup, no-contact, no-response, unresponsive, missing")
                return
            
            # Get the specific category quickly
            result = self.collections_tracker.get_stale_cases_by_category(
                self.case_manager, 
                internal_category, 
                limit=10
            )
            
            cases = result["cases"]
            total = result["total"]
            remaining = result["remaining"]
            
            # Display friendly category name
            friendly_names = {
                "critical": "CRITICAL CASES (90+ days)",
                "high_priority": "HIGH PRIORITY CASES (60+ days, no response)",
                "needs_follow_up": "FOLLOW-UP NEEDED (30+ days)", 
                "no_contact": "NO CONTACT (Never contacted)",
                "no_response": "NO RESPONSE (Emails sent, no replies)",
                "unresponsive_firms": "UNRESPONSIVE FIRMS (Multiple contacts, no response)",
                "missing_from_bootstrap": "MISSING FROM BOOTSTRAP (Need backfill)"
            }
            
            category_title = friendly_names.get(internal_category, category.title())
            
            print(f"\n{'='*60}")
            print(f"🎯 {category_title}")
            print(f"{'='*60}")
            
            if not cases:
                print(f"\n🎉 No {category} cases found!")
                return
            
            print(f"\nShowing {len(cases)} of {total} total cases:")
            print("-" * 50)
            
            for i, case in enumerate(cases, 1):
                print(f"{i}. PV {case['pv']} - {case['name']}")
                if case.get('days_since_contact'):
                    print(f"   📅 {case['days_since_contact']} days since last contact")
                else:
                    print(f"   📅 No recorded contact")
                print(f"   🏛️  {case.get('law_firm', 'Unknown Firm')}")
                print(f"   📧 {case.get('attorney_email', 'No email')}")
                
                # Show activity summary
                activity_count = case.get('activity_count', 0)
                response_count = case.get('response_count', 0)
                print(f"   📊 Activities: {activity_count} | Responses: {response_count}")
                print()
            
            if remaining > 0:
                print(f"... and {remaining} more {category} cases")
            
            print(f"\n💡 QUICK ACTIONS:")
            print(f"• Use 'summarize pv <number>' to review a specific case")
            print(f"• Use 'draft follow-up for <pv>' to create follow-up email")
            print(f"• Use 'draft status request for <pv>' for initial contact")
            
            # Ask if user wants to work on any cases
            if cases:
                print(f"\nWork on a case now? Enter PV number or 'skip':")
                choice = input("> ").strip()
                
                if choice.lower() != 'skip' and choice.isdigit():
                    # Check if the PV is in our list
                    case_pvs = [case['pv'] for case in cases]
                    if choice in case_pvs:
                        case = self.case_manager.get_case_by_pv(choice)
                        if case:
                            self.summarize_case(case)
                    else:
                        print(f"❌ PV {choice} not found in {category} cases")
            
        except Exception as e:
            logger.error(f"Error showing stale category {category}: {e}")
            print(f"❌ Error showing {category} cases: {e}")
    
    def _run_gmail_setup(self):
        """Run Gmail setup for team members"""
        try:
            # Use simplified team setup
            from team_gmail_setup import TeamGmailSetup
            setup = TeamGmailSetup()
            
            if setup.run():
                # Reinitialize Gmail service with new credentials
                try:
                    from services.gmail_service import GmailService
                    from services.email_cache_service import EmailCacheService
                    self.gmail_service = GmailService()
                    self.email_cache_service = EmailCacheService(self.gmail_service)
                    print("\n✅ Services reloaded with your Gmail account!")
                except Exception as e:
                    print(f"\n⚠️ Please restart the application to complete setup: {e}")
        except Exception as e:
            logger.error(f"Gmail setup error: {e}")
            print(f"\n❌ Error running setup: {e}")
            print("Please contact Dean to get the credentials.json file.")
    
    def _show_help(self):
        """Display all available commands"""
        print("\n" + "="*60)
        print("📋 AVAILABLE COMMANDS")
        print("="*60)
        print()
        
        print("📊 CASE ANALYSIS:")
        print("  summarize pv <number>     - Summarize case and emails (with suggestions)")
        print("  summarize <name>          - Summarize case by name")
        print()
        
        print("✍️  EMAIL DRAFTING:")
        print("  draft follow-up for <pv>  - Draft follow-up email")
        print("  draft status request for <pv> - Draft status request")
        print()
        
        print("📨 BULK EMAIL PROCESSING:")
        print("  bulk start                - Start bulk email wizard")
        print("  bulk test on/off          - Toggle test mode for bulk emails")
        print("  bulk stats                - Show bulk processing statistics")
        print("  bulk export               - Export current batch for review")
        print("  check pending cms         - Check emails waiting for CMS notes")
        print("  add session cms notes     - Process all pending CMS notes")
        print()
        
        print("📈 COLLECTIONS MANAGEMENT:")
        print("  collections dashboard     - Show collections performance summary")
        print("  stale cases               - Show comprehensive stale case analysis")
        print("  bootstrap emails          - Download ALL emails to cache (run this first!)")
        print("  bootstrap collections     - Analyze cached emails for tracking")
        print()
        
        print("📋 STALE CASE LISTS (Quick Access):")
        print("  list critical             - Show critical cases (90+ days)")
        print("  list high-priority        - Show high priority cases (60+ days)")
        print("  list needs-followup       - Show cases needing follow-up (30+ days)")
        print("  list no-contact           - Show cases never contacted")
        print("  list no-response          - Show cases with emails sent but no replies")
        print("  list unresponsive         - Show cases with unresponsive firms") 
        print("  list missing              - Show cases missing from bootstrap")
        print()
        
        print("⚙️  SYSTEM:")
        print("  refresh email cache       - Update email cache and cadence analysis")
        print("  backfill missing          - Fill in cases that bootstrap missed")
        print("  show cadence              - Display your email writing style analysis")
        print("  clear cache               - Clear stale case cache (force fresh analysis)")
        print("  help                      - Show this help message")
        print("  exit                      - Quit application")
        print()
        
        print("💡 TIP: Use 'list critical' to start working on the most urgent cases!")
        print("💡 TIP: After sending follow-ups, cases automatically move out of stale categories.")
        print()
    
    def _run_bulk_email_wizard(self):
        """Interactive bulk email processing wizard"""
        try:
            print("\n" + "="*60)
            print("📨 BULK EMAIL PROCESSING WIZARD")
            print("="*60)
            
            # Show test mode status with emphasis
            if self.bulk_email_service.test_mode:
                print("╔" + "═"*58 + "╗")
                print("║" + " "*21 + "⚠️  TEST MODE ACTIVE" + " "*16 + "║")
                print(f"║  Emails will go to: {self.bulk_email_service.test_email:<34} ║")
                print("║  Categories will NOT be updated" + " "*24 + "║")
                print("║  No production tracking will occur" + " "*21 + "║")
                print("╚" + "═"*58 + "╝")
            else:
                print("⚡ PRODUCTION MODE - Emails will go to actual recipients")
            
            # Categorize cases
            print("\n📊 Categorizing cases...")
            categories = self.bulk_email_service.categorize_cases()
            
            # Show statistics
            print("\n📈 Available Cases:")
            print(f"  • Missing DOI: {len(categories['missing_doi'])} cases")
            print(f"  • Old cases (>2 years): {len(categories['old_cases'])} cases")
            print(f"  • No recent contact: {len(categories['no_recent_contact'])} cases")
            print(f"  • Never contacted: {len(categories['never_contacted'])} cases")
            print(f"  • By priority score: {len(categories.get('by_priority', {}).get('high', []))} high, {len(categories.get('by_priority', {}).get('medium', []))} medium")
            print(f"  • Unique firms: {len(categories['by_firm'])} firms")
            
            while True:
                # Check for pending CMS notes
                pending_count = 0
                try:
                    from services.cms_integration import get_session_stats
                    stats = get_session_stats()
                    pending_count = stats.get('pending_count', 0)
                except:
                    pass
                
                print("\n" + "-"*60)
                print("SELECT PROCESSING MODE:")
                print("  [1] Process by category")
                print("  [2] Process by firm")
                print("  [3] Process custom selection")
                print("  [4] Process by priority score 🎯")
                print("  [5] Paste PV/CMS numbers 📋")
                print("  [6] Toggle test mode")
                print("  [7] View statistics")
                if pending_count > 0:
                    print(f"  [C] Process pending CMS notes 📝 ({pending_count} pending)")
                else:
                    print("  [C] Process pending CMS notes 📝")
                print("  [Q] Exit bulk processing")
                print("-"*60)
                
                choice = input("\nYour choice: ").strip().upper()
                
                if choice == "1":
                    self._process_by_category()
                    
                elif choice == "2":
                    self._process_by_firm()
                    
                elif choice == "3":
                    self._process_custom_selection()
                    
                elif choice == "4":
                    self._process_by_priority()
                    
                elif choice == "5":
                    self._process_paste_numbers()
                    
                elif choice == "6":
                    current_mode = self.bulk_email_service.test_mode
                    if current_mode:
                        self.bulk_email_service.set_test_mode(False)
                        print("✅ Test mode DISABLED - emails will go to actual recipients")
                    else:
                        test_email = input("Enter test email address (Enter for default): ").strip()
                        self.bulk_email_service.set_test_mode(True, test_email if test_email else None)
                        print(f"✅ Test mode ENABLED - emails will go to: {self.bulk_email_service.test_email}")
                    
                elif choice == "7":
                    stats = self.bulk_email_service.get_statistics()
                    print("\n📊 Bulk Processing Statistics:")
                    print(f"  • Test mode: {'ON' if stats['test_mode'] else 'OFF'}")
                    print("\n📧 Production Emails:")
                    print(f"  • Sent this session: {stats.get('session_sent_production', 0)}")
                    print(f"  • Total sent (all time): {stats.get('total_sent_production', 0)}")
                    print("\n🧪 Test Emails:")
                    print(f"  • Test emails sent: {stats.get('test_emails_sent', 0)}")
                    if stats['categories']:
                        print("\n📂 Available Categories:")
                        for cat, count in stats['categories'].items():
                            if isinstance(count, dict):
                                print(f"    • {cat}: {count['firms']} firms, {count['total_cases']} cases")
                            else:
                                print(f"    • {cat}: {count} cases")
                    
                elif choice == "C":
                    print("\n🔄 Processing pending CMS notes...")
                    try:
                        from services.cms_integration import process_session_cms_notes
                        import asyncio
                        success = asyncio.run(process_session_cms_notes())
                        if success:
                            print("✅ All pending CMS notes processed successfully!")
                        else:
                            print("⚠️  Some CMS notes may have failed - check logs")
                        input("\nPress Enter to continue...")
                    except Exception as e:
                        logger.error(f"Error processing CMS notes: {e}")
                        print(f"❌ Error processing CMS notes: {e}")
                        input("\nPress Enter to continue...")
                    
                elif choice == "Q":
                    print("Exiting bulk processing...")
                    break
                    
                else:
                    print("Invalid choice. Please try again.")
                    
        except Exception as e:
            logger.error(f"Error in bulk email wizard: {e}")
            print(f"❌ Error: {e}")
    
    def _process_by_category(self):
        """Process emails by category"""
        try:
            print("\n📂 SELECT CATEGORY:")
            print("  [1] Never contacted")
            print("  [2] No recent contact (>60 days)")
            print("  [3] Missing DOI")
            print("  [4] Old cases (>2 years)")
            print("  [B] Back")
            
            choice = input("\nYour choice: ").strip().upper()
            
            category_map = {
                "1": "never_contacted",
                "2": "no_recent_contact",
                "3": "missing_doi",
                "4": "old_cases"
            }
            
            if choice in category_map:
                category = category_map[choice]
                
                limit = input("How many to process? (Enter for all): ").strip()
                limit = int(limit) if limit else None
                
                # Prepare batch
                emails = self.bulk_email_service.prepare_batch(category, limit=limit)
                
                if not emails:
                    print(f"No cases found in category: {category}")
                    return
                
                # Get approval
                approved, action = self.bulk_email_service.get_approval_for_batch(emails)
                
                if approved:
                    # Send approved emails
                    results = self.bulk_email_service.send_batch(approved)
                    
                    # Show results
                    print(f"\n✅ Batch complete!")
                    print(f"   Sent: {len(results['sent'])}")
                    print(f"   Failed: {len(results['failed'])}")
                    if len(results['sent']) > 0:
                        print("\n💡 TIP: Press [C] to process pending CMS notes")
                else:
                    print("Batch skipped.")
                    
        except Exception as e:
            logger.error(f"Error processing by category: {e}")
            print(f"❌ Error: {e}")
    
    def _process_by_firm(self):
        """Process emails by law firm"""
        try:
            categories = self.bulk_email_service.categorized_cases
            firms = categories.get("by_firm", {})
            
            if not firms:
                print("No firms with cases found.")
                return
            
            print("\n🏢 FIRMS WITH CASES:")
            firm_list = list(firms.keys())
            for i, firm in enumerate(firm_list[:20], 1):  # Show first 20
                print(f"  [{i}] {firm} ({len(firms[firm])} cases)")
            
            if len(firm_list) > 20:
                print(f"  ... and {len(firm_list) - 20} more firms")
            
            print("\nEnter firm number or email address:")
            choice = input("> ").strip()
            
            # Determine selected firm
            selected_firm = None
            if choice.isdigit() and 1 <= int(choice) <= len(firm_list):
                selected_firm = firm_list[int(choice) - 1]
            elif "@" in choice and choice in firms:
                selected_firm = choice
            
            if not selected_firm:
                print("Invalid selection.")
                return
            
            limit = input(f"How many cases to process for {selected_firm}? (Enter for all): ").strip()
            limit = int(limit) if limit else None
            
            # Prepare batch
            emails = self.bulk_email_service.prepare_batch("by_firm", subcategory=selected_firm, limit=limit)
            
            if not emails:
                print(f"No cases found for firm: {selected_firm}")
                return
            
            # Get approval
            approved, action = self.bulk_email_service.get_approval_for_batch(emails)
            
            if approved:
                # Send approved emails
                results = self.bulk_email_service.send_batch(approved)
                
                # Show results
                print(f"\n✅ Batch complete!")
                print(f"   Sent: {len(results['sent'])}")
                print(f"   Failed: {len(results['failed'])}")
                if len(results['sent']) > 0:
                    print("\n💡 TIP: Press [C] to process pending CMS notes")
            else:
                print("Batch skipped.")
                
        except Exception as e:
            logger.error(f"Error processing by firm: {e}")
            print(f"❌ Error: {e}")
    
    def _process_custom_selection(self):
        """Process custom selection of cases"""
        try:
            print("\n📝 CUSTOM SELECTION")
            print("Enter PV numbers separated by commas (e.g., 12345,67890,11111):")
            
            pv_input = input("> ").strip()
            pvs = [pv.strip() for pv in pv_input.split(",")]
            
            # Prepare emails for selected PVs
            emails = []
            for pv in pvs:
                case = self.case_manager.get_case_by_pv(pv)
                if case:
                    case_data = {
                        "pv": pv,
                        "name": case.get("Name", ""),
                        "doi": case.get("DOI", ""),
                        "cms": case.get("CMS", ""),
                        "attorney_email": case.get("Attorney Email", ""),
                        "law_firm": case.get("Law Firm", ""),
                        "status": case.get("Status", ""),
                        "full_case": case
                    }
                    
                    try:
                        email = self.bulk_email_service.generate_email_content(case_data)
                        emails.append(email)
                    except Exception as e:
                        print(f"❌ Error generating email for PV {pv}: {e}")
                else:
                    print(f"⚠️  PV {pv} not found")
            
            if not emails:
                print("No valid cases found.")
                return
            
            # Get approval
            approved, action = self.bulk_email_service.get_approval_for_batch(emails)
            
            if approved:
                # Send approved emails
                results = self.bulk_email_service.send_batch(approved)
                
                # Show results
                print(f"\n✅ Batch complete!")
                print(f"   Sent: {len(results['sent'])}")
                print(f"   Failed: {len(results['failed'])}")
                if len(results['sent']) > 0:
                    print("\n💡 TIP: Press [C] to process pending CMS notes")
            else:
                print("Batch skipped.")
                
        except Exception as e:
            logger.error(f"Error processing custom selection: {e}")
            print(f"❌ Error: {e}")
    
    def _process_by_priority(self):
        """Process emails by priority score"""
        try:
            print("\n🎯 PROCESS BY PRIORITY SCORE")
            print("Cases are scored 0-100 based on:")
            print("  • Firm responsiveness history (40 points)")
            print("  • Optimal case age (30 points)")
            print("  • Days since last contact (20 points)")
            print("  • Other factors (10 points)")
            print()
            print("Select priority range:")
            print("  [1] High priority (70-100 score)")
            print("  [2] Medium priority (40-69 score)")
            print("  [3] Low priority (0-39 score)")
            print("  [4] Show score breakdown")
            print("  [B] Back")
            
            choice = input("\nYour choice: ").strip().upper()
            
            if choice == "4":
                # Show detailed scoring breakdown
                print("\n📊 PRIORITY SCORING BREAKDOWN:")
                print("\nFirm Responsiveness (0-40 points):")
                print("  • Based on historical response rates from each firm")
                print("  • High responders get higher priority")
                print("\nCase Age Sweet Spot (0-30 points):")
                print("  • 3-6 months old: 30 points (peak settlement window)")
                print("  • 6-12 months: 20 points")
                print("  • 1-2 years: 10 points")
                print("  • Other ages: 5 points")
                print("\nDays Since Contact (0-20 points):")
                print("  • Never contacted: 20 points")
                print("  • 30-60 days: 15 points")
                print("  • 60-90 days: 10 points")
                print("  • 90+ days: 5 points")
                print("\nOther Factors (0-10 points):")
                print("  • Has DOI: +5 points")
                print("  • Active status: +5 points")
                return
            
            priority_map = {
                "1": "high",
                "2": "medium",
                "3": "low"
            }
            
            if choice in priority_map:
                priority_level = priority_map[choice]
                
                limit = input("How many to process? (Enter for all): ").strip()
                limit = int(limit) if limit else None
                
                # Prepare batch by priority
                emails = self.bulk_email_service.prepare_batch("by_priority", subcategory=priority_level, limit=limit)
                
                if not emails:
                    print(f"No cases found in {priority_level} priority")
                    return
                
                # Show priority scores for first few
                print(f"\n📊 Sample of {priority_level} priority cases:")
                for email in emails[:3]:
                    print(f"  • {email['name']} (PV {email['pv']}): Score {email.get('priority_score', 'N/A')}")
                if len(emails) > 3:
                    print(f"  ... and {len(emails) - 3} more")
                
                # Handle batch processing
                self._handle_batch_processing(emails)
                
        except Exception as e:
            logger.error(f"Error processing by priority: {e}")
            print(f"❌ Error: {e}")
    
    def _process_paste_numbers(self):
        """Process bulk send from pasted PV/CMS numbers"""
        try:
            print("\n📋 PASTE PV/CMS NUMBERS")
            print("Paste a list of PV or CMS numbers (one per line or comma-separated)")
            print("Press Enter twice when done:")
            print()
            
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            
            if not lines:
                print("No numbers provided")
                return
            
            # Parse numbers (could be comma-separated or newline-separated)
            numbers = []
            for line in lines:
                if ',' in line:
                    numbers.extend([n.strip() for n in line.split(',')])
                else:
                    numbers.append(line.strip())
            
            # Clean up numbers
            numbers = [n for n in numbers if n]
            
            print(f"\n🔍 Found {len(numbers)} numbers to process")
            
            # Use the bulk service's new method
            emails = self.bulk_email_service.prepare_batch_from_numbers(numbers)
            
            if not emails:
                print("No valid cases found for the provided numbers")
                return
            
            print(f"✅ Found {len(emails)} valid cases")
            
            # Handle batch processing
            self._handle_batch_processing(emails)
            
        except Exception as e:
            logger.error(f"Error processing pasted numbers: {e}")
            print(f"❌ Error: {e}")
    
    def _handle_batch_processing(self, emails):
        """Common batch processing logic"""
        try:
            # Get approval
            approved, action = self.bulk_email_service.get_approval_for_batch(emails)
            
            if approved:
                # Send approved emails
                results = self.bulk_email_service.send_batch(approved)
                
                # Show results
                print(f"\n✅ Batch complete!")
                print(f"   Sent: {len(results['sent'])}")
                print(f"   Failed: {len(results['failed'])}")
                if len(results['sent']) > 0:
                    print("\n💡 TIP: Press [C] to process pending CMS notes")
                
                if results['failed']:
                    print("\n❌ Failed emails:")
                    for fail in results['failed'][:5]:
                        print(f"   • {fail['pv']}: {fail['error']}")
                    if len(results['failed']) > 5:
                        print(f"   ... and {len(results['failed']) - 5} more")
            else:
                print("Batch skipped.")
                
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            print(f"❌ Error: {e}")
    
    def _check_pending_cms_notes(self):
        """Check and display pending CMS notes that haven't been processed yet"""
        try:
            from services.cms_integration import load_pending_emails, get_session_stats
            
            print("\n" + "="*60)
            print("📋 CMS NOTES STATUS CHECK")
            print("="*60)
            
            # Get session stats
            stats = get_session_stats()
            
            print(f"\n📊 Session Statistics:")
            print(f"  • Emails pending CMS notes: {stats['pending_count']}")
            print(f"  • Emails with CMS notes added: {stats['processed_count']}")
            print(f"  • Total CMS notes in log: {stats['cms_notes_count']}")
            
            # Load pending emails
            pending = load_pending_emails()
            
            if not pending:
                print("\n✅ All emails have CMS notes! Nothing pending.")
                return
            
            print(f"\n⚠️  {len(pending)} emails waiting for CMS notes:")
            print("-" * 50)
            
            # Group by email type
            by_type = {}
            for pid, info in pending.items():
                email_type = info.get('email_type', 'UNKNOWN')
                if email_type not in by_type:
                    by_type[email_type] = []
                by_type[email_type].append({
                    'pid': pid,
                    'email': info.get('email', 'N/A')
                })
            
            # Display by type
            for email_type, items in by_type.items():
                print(f"\n📧 {email_type} ({len(items)} pending):")
                for item in items[:5]:  # Show first 5 of each type
                    print(f"  • PID {item['pid']} → {item['email']}")
                if len(items) > 5:
                    print(f"  ... and {len(items) - 5} more")
            
            print("\n💡 Actions:")
            print("  • Run 'add session cms notes' to process these")
            print("  • Check 'session_emails_pending.log' for full list")
            print("  • Emails will remain pending until CMS notes are added")
            
            # Check for test vs production
            test_count = sum(1 for info in pending.values() if 'test_' in info.get('email_type', '').lower())
            prod_count = len(pending) - test_count
            
            if test_count > 0:
                print(f"\n🧪 Test emails pending: {test_count}")
            if prod_count > 0:
                print(f"📧 Production emails pending: {prod_count}")
            
        except Exception as e:
            logger.error(f"Error checking pending CMS notes: {e}")
            print(f"❌ Error checking pending CMS notes: {e}")
    
    def _backfill_missing_cases(self):
        """Backfill cases that bootstrap missed"""
        try:
            print("\n🔄 BACKFILLING MISSING CASES")
            print("="*50)
            print("This will search Gmail for cases that bootstrap missed and add them to the cache.")
            
            confirm = input("\nProceed with backfill? (y/n): ").strip().lower()
            if confirm != "y":
                print("❌ Backfill cancelled")
                return
            
            print("\n🔍 Starting backfill process...")
            result = self.collections_tracker.backfill_missing_cases(
                self.gmail_service,
                self.case_manager
            )
            
            print(f"\n✅ BACKFILL COMPLETE!")
            print(f"📊 Results:")
            print(f"   • Processed: {result['processed']} cases")
            print(f"   • Found data for: {result['found']} cases")
            print(f"   • Message: {result['message']}")
            
            if result['found'] > 0:
                print(f"\n💡 Next steps:")
                print(f"   • Run 'clear cache' to refresh stale analysis")
                print(f"   • Run 'stale cases' to see updated categorization")
            
        except Exception as e:
            logger.error(f"Error during backfill: {e}")
            print(f"❌ Error during backfill: {e}")
    
    def draft_followup_email(self, case):
        """Draft and optionally send follow-up email"""
        try:
            print(f"🧠 Drafting follow-up email for {case['Name']}...")
            
            # Search for email threads (use same query as summarize for consistency)
            query = self._build_search_query(case)
            logger.debug(f"Follow-up search query: {query}")
            message_results = self.gmail_service.search_messages(query)
            
            if not message_results:
                print("❌ No email threads found. Use 'draft status request for <pv>' to send a new email.")
                return
            
            # Get full threads
            thread_messages = []
            for msg in message_results:
                if "id" in msg:
                    thread = self.gmail_service.get_thread(msg["id"])
                    if thread:
                        thread_messages.append(thread)
                        # DEBUG: Log thread structure
                        logger.info(f"Thread structure keys: {list(thread.keys()) if isinstance(thread, dict) else 'Not a dict'}")
                        if isinstance(thread, dict) and 'messages' in thread:
                            logger.info(f"Thread has {len(thread['messages'])} messages")
            
            if not thread_messages:
                print("❌ No valid reply threads found.")
                return
            
            # Generate email with cadence guidance
            cadence_guidance = self.email_cache_service.get_cadence_guidance()
            email_body = self.ai_service.generate_followup_email(case, thread_messages, cadence_guidance)
            
            # Choose recipient (simplified for now)
            recipient_email = case.get('Attorney Email', '')
            if not recipient_email:
                recipient_email = input("Enter recipient email: ").strip()
            
            # Get thread ID for reply
            thread_id = message_results[0].get('thread_id') if message_results else None
            
            print("\n✉️ Follow-Up Email Preview:")
            print(f"To: {recipient_email}")
            print(f"Thread ID: {thread_id}")
            print("-" * 50)
            print(email_body)
            print("-" * 50)
            
            # Confirm sending
            confirm = input("\n✅ Send this follow-up as a reply? (y/n): ").strip().lower()
            if confirm == "y":
                msg_id = self.gmail_service.send_email(
                    recipient_email, None, email_body, thread_id=thread_id
                )
                print(f"📬 Email sent! Gmail ID: {msg_id}")
                log_sent_email(case['PV'], recipient_email, f"Follow-up reply", msg_id)
                
                # Invalidate stale case cache so this case gets recategorized immediately
                self.collections_tracker.invalidate_stale_case_cache()
                print("🔄 Case categories refreshed")
                
                # Add note to CMS system
                try:
                    import asyncio
                    print("📝 Adding note to CMS system...")
                    success = asyncio.run(add_cms_note_for_email(case, "follow_up", recipient_email))
                    if success:
                        print("✅ CMS note added successfully")
                    else:
                        print("⚠️ CMS note failed - check logs")
                except Exception as e:
                    logger.error(f"Error adding CMS note: {e}")
                    print(f"⚠️ CMS note error: {e}")
            else:
                print("✉️ Email not sent.")
                
        except Exception as e:
            logger.error(f"Error drafting follow-up email: {e}")
            print(f"❌ Error: {e}")
    
    def draft_status_request(self, case):
        """Draft and optionally send status request email"""
        try:
            email_body = self.ai_service.generate_status_request_email(case)
            subject = f"{case['Name'].upper()} DOI {case['DOI']} // Prohealth Advanced Imaging"
            
            print("\n✉️ Status Request Email Preview:")
            print(f"Subject: {subject}")
            print("-" * 50)
            print(email_body)
            print("-" * 50)
            
            # Choose recipient
            recipient_email = case.get('Attorney Email', '')
            if not recipient_email or not '@' in recipient_email:
                recipient_email = input("Enter recipient email: ").strip()
            
            confirm = input(f"\n✅ Send this status request to {recipient_email}? (y/n): ").strip().lower()
            if confirm == "y":
                msg_id = self.gmail_service.send_email(recipient_email, subject, email_body)
                print(f"📬 Email sent! Gmail ID: {msg_id}")
                log_sent_email(case['PV'], recipient_email, subject, msg_id)
                
                # Invalidate stale case cache so this case gets recategorized immediately
                self.collections_tracker.invalidate_stale_case_cache()
                print("🔄 Case categories refreshed")
                
                # Add note to CMS system
                try:
                    import asyncio
                    print("📝 Adding note to CMS system...")
                    success = asyncio.run(add_cms_note_for_email(case, "status_request", recipient_email))
                    if success:
                        print("✅ CMS note added successfully")
                    else:
                        print("⚠️ CMS note failed - check logs")
                except Exception as e:
                    logger.error(f"Error adding CMS note: {e}")
                    print(f"⚠️ CMS note error: {e}")
            else:
                print("✉️ Email not sent.")
                
        except Exception as e:
            logger.error(f"Error drafting status request: {e}")
            print(f"❌ Error: {e}")
    
    def run(self):
        """Main application loop"""
        print("[AI] Welcome to your AI Case Assistant!")
        print("Commands:")
        print("- summarize pv <number>     : Summarize case and emails (with suggestions)")
        print("- summarize <name>          : Summarize case by name")
        print("- draft follow-up for <pv>  : Draft follow-up email")
        print("- draft status request for <pv> : Draft status request")
        print("- refresh email cache       : Update email cache and cadence analysis")
        print("- show cadence              : Display your email writing style analysis")
        print("- collections dashboard     : Show collections performance summary")
        print("- stale cases               : Show cases needing follow-up")
        print("- list critical             : Show critical cases (90+ days)")
        print("- list high-priority        : Show high priority cases (60+ days)")
        print("- list needs-followup       : Show cases needing follow-up (30+ days)")
        print("- list no-contact           : Show cases never contacted")
        print("- list no-response          : Show cases with emails sent but no replies")
        print("- list unresponsive         : Show cases with unresponsive firms")
        print("- list missing              : Show cases missing from bootstrap")
        print("- bootstrap emails          : Download ALL emails to cache (RUN THIS FIRST!)")
        print("- bootstrap collections     : Analyze cached emails (run AFTER bootstrap emails)")
        print("- backfill missing          : Fill in cases that bootstrap missed")
        print("- bulk start                : Start bulk email processing wizard")
        print("- bulk test on/off          : Toggle test mode for bulk emails")
        print("- bulk stats                : Show bulk processing statistics")
        print("- check pending cms         : Check emails waiting for CMS notes")
        print("- add session cms notes     : Process pending CMS notes (run after sending emails)")
        print("- init cms                  : Initialize CMS browser session (one-time setup)")
        print("- gmail setup               : Setup Gmail for new users (OAuth & configuration)")
        print("- help                      : Show all available commands")
        print("- exit                      : Quit application")
        print()
        
        while True:
            try:
                cmd = input("> ").strip().lower()
                
                if cmd in ["exit", "quit"]:
                    print("Goodbye!")
                    break
                
                elif cmd.startswith("summarize pv "):
                    pv = cmd.replace("summarize pv ", "").strip()
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        self.summarize_case(case)
                    else:
                        print("❌ Case not found.")
                
                elif cmd.startswith("summarize "):
                    name = cmd.replace("summarize ", "").strip()
                    case = self.case_manager.get_case_by_name(name)
                    if case:
                        self.summarize_case(case)
                    else:
                        print("❌ Case not found.")
                
                elif cmd.startswith("draft follow-up for "):
                    pv = cmd.replace("draft follow-up for ", "").strip()
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        self.draft_followup_email(case)
                    else:
                        print("❌ Case not found.")
                
                elif cmd.startswith("draft status request for "):
                    pv = cmd.replace("draft status request for ", "").strip()
                    case = self.case_manager.get_case_by_pv(pv)
                    if case:
                        self.draft_status_request(case)
                    else:
                        print("❌ Case not found.")
                
                elif cmd == "refresh email cache":
                    print("📥 Refreshing email cache and analyzing cadence...")
                    self.email_cache_service.download_sent_emails(500)
                    print("✅ Email cache refreshed!")
                
                elif cmd == "show cadence":
                    self.email_cache_service._display_cadence_summary()
                
                elif cmd == "collections dashboard":
                    self._show_collections_dashboard()
                
                elif cmd == "stale cases":
                    self._show_comprehensive_stale_cases()
                
                elif cmd == "bootstrap emails":
                    # Bootstrap the email cache with ALL emails
                    print("\n🚀 Bootstrapping email cache with ALL emails (sent & received)...")
                    print("⚠️  This may take 10-30 minutes depending on your email volume.")
                    confirm = input("\nProceed with full email download? (y/n): ").strip().lower()
                    if confirm == 'y':
                        try:
                            emails = self.email_cache_service.bootstrap_all_emails()
                            print(f"\n✅ Downloaded {len(emails)} emails to cache!")
                            print("📊 Now run 'bootstrap collections' to analyze them.")
                        except Exception as e:
                            logger.error(f"Email bootstrap error: {e}")
                            print(f"❌ Error bootstrapping emails: {e}")
                    else:
                        print("Bootstrap cancelled.")
                    
                elif cmd == "bootstrap collections":
                    # Try enhanced tracker first if available
                    if hasattr(self, 'enhanced_tracker') and self.enhanced_tracker:
                        print("\n🚀 Using enhanced collections tracker with cache...")
                        print("This will be MUCH faster than direct Gmail queries!")
                        try:
                            success = self.enhanced_tracker.analyze_from_cache(self.case_manager)
                            if success:
                                print("✅ Collections analysis complete!")
                                # Don't show results here - already shown by the tracker
                                # The enhanced tracker prints its own summary
                            else:
                                print("⚠️ Cache-based analysis failed, using standard bootstrap...")
                                self._bootstrap_collections_tracker()
                        except Exception as e:
                            logger.error(f"Enhanced tracker error: {e}")
                            print("⚠️ Error with enhanced tracker, using standard bootstrap...")
                            self._bootstrap_collections_tracker()
                    else:
                        self._bootstrap_collections_tracker()
                
                elif cmd == "init cms":
                    print("🚀 Initializing CMS browser session...")
                    print("📋 A browser will open - please manually click 'Cancel' on the certificate popup")
                    print("   (This is a one-time setup to avoid future popups)")
                    print()
                    
                    try:
                        import asyncio
                        success = asyncio.run(self.initialize_cms_session())
                        if success:
                            print("✅ CMS session initialized! Browser will stay open.")
                            print("🎉 Future emails will add CMS notes automatically!")
                        else:
                            print("❌ CMS session initialization failed.")
                            print("   You can try again with 'init cms' command")
                    except Exception as e:
                        print(f"❌ CMS initialization error: {e}")
                
                elif cmd.startswith("list "):
                    category = cmd.replace("list ", "").strip()
                    self._show_stale_category(category)
                
                elif cmd == "gmail setup":
                    self._run_gmail_setup()
                
                elif cmd == "help":
                    self._show_help()
                
                elif cmd == "clear cache":
                    self.collections_tracker.clear_stale_cache()
                    print("✅ Stale case cache cleared - next 'stale cases' will be fresh analysis")
                
                elif cmd == "backfill missing":
                    self._backfill_missing_cases()
                
                elif cmd == "check pending cms":
                    self._check_pending_cms_notes()
                
                elif cmd == "add session cms notes":
                    print("🔄 Processing pending CMS notes...")
                    try:
                        from services.cms_integration import process_session_cms_notes
                        import asyncio
                        success = asyncio.run(process_session_cms_notes())
                        if success:
                            print("✅ All pending CMS notes processed successfully!")
                        else:
                            print("⚠️  Some CMS notes may have failed - check logs")
                    except Exception as e:
                        logger.error(f"Error processing CMS notes: {e}")
                        print(f"❌ Error processing CMS notes: {e}")
                
                elif cmd == "bulk start":
                    self._run_bulk_email_wizard()
                
                elif cmd == "bulk test on":
                    test_email = input("Enter test email address (Enter for default): ").strip()
                    result = self.bulk_email_service.set_test_mode(True, test_email if test_email else None)
                    print(f"✅ {result}")
                
                elif cmd == "bulk test off":
                    result = self.bulk_email_service.set_test_mode(False)
                    print(f"✅ {result}")
                
                elif cmd == "bulk stats":
                    stats = self.bulk_email_service.get_statistics()
                    print("\n📊 Bulk Processing Statistics:")
                    print(f"  • Test mode: {'ON' if stats['test_mode'] else 'OFF'}")
                    if stats['test_mode']:
                        print(f"  • Test email: {stats['test_email']}")
                    print("\n📧 Production Emails:")
                    print(f"  • Sent this session: {stats.get('session_sent_production', 0)}")
                    print(f"  • Total sent (all time): {stats.get('total_sent_production', 0)}")
                    print("\n🧪 Test Emails:")
                    print(f"  • Test emails sent: {stats.get('test_emails_sent', 0)}")
                
                elif cmd == "bulk export":
                    if self.bulk_email_service.email_queue:
                        filepath = self.bulk_email_service.export_batch_for_review(self.bulk_email_service.email_queue)
                        print(f"✅ Batch exported to: {filepath}")
                    else:
                        print("❌ No batch currently loaded. Use 'bulk start' first.")
                
                else:
                    print("🤷 Command not recognized. Type 'help' to see all commands.")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                print(f"❌ Unexpected error: {e}")

def main():
    """Application entry point"""
    try:
        # Fix Windows encoding issues
        if sys.platform == "win32":
            import os
            os.system("chcp 65001 >nul 2>&1")  # Set console to UTF-8
        
        # Setup logging
        setup_logging()
        logger.info("AI Assistant starting up")
        
        # Create and run application
        app = AssistantApp()
        app.run()
        
    except Exception as e:
        print(f"[ERROR] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""
Case Acknowledgment Service
Manages acknowledged/snoozed cases that don't need immediate follow-up
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from config import Config

logger = logging.getLogger(__name__)

# Import CMS logging function for acknowledgments
try:
    from services.cms_integration import log_acknowledgment_note
    CMS_AVAILABLE = True
except ImportError:
    CMS_AVAILABLE = False
    logger.warning("CMS integration not available for acknowledgment notes")

class CaseAcknowledgmentService:
    """Service to manage acknowledged/snoozed cases"""
    
    def __init__(self):
        self.ack_file = Config.get_file_path("data/acknowledged_cases.json")
        self.acknowledged_cases = self._load_acknowledgments()
        # Clean up expired acknowledgments on init
        self._cleanup_expired()
    
    def _load_acknowledgments(self) -> Dict:
        """Load acknowledged cases from file"""
        if os.path.exists(self.ack_file):
            try:
                with open(self.ack_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                logger.error(f"Error loading acknowledgments: {e}")
                return {}
        return {}
    
    def _save_acknowledgments(self):
        """Save acknowledgments to file"""
        try:
            os.makedirs(os.path.dirname(self.ack_file), exist_ok=True)
            with open(self.ack_file, 'w', encoding='utf-8') as f:
                json.dump(self.acknowledged_cases, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving acknowledgments: {e}")
    
    def acknowledge_case(self, pv: str, reason: str = "", snooze_days: int = 30, 
                        status: str = "", notes: str = "", cms_number: str = None) -> bool:
        """
        Acknowledge a case to temporarily remove it from active workflows
        
        Args:
            pv: Case PV number
            reason: Reason for acknowledgment (e.g., "LITIGATION", "PENDING SETTLEMENT")
            snooze_days: Number of days to snooze (0 = indefinite)
            status: Current case status from xlsx
            notes: Additional notes
            cms_number: CMS/PID number for the case (optional)
        
        Returns:
            bool: Success status
        """
        try:
            ack_data = {
                "acknowledged_date": datetime.now().isoformat(),
                "acknowledged_by": "user",
                "reason": reason,
                "status": status,
                "notes": notes,
                "snooze_days": snooze_days,
                "review_after": None if snooze_days == 0 else 
                               (datetime.now() + timedelta(days=snooze_days)).isoformat()
            }
            
            self.acknowledged_cases[str(pv)] = ack_data
            self._save_acknowledgments()
            
            logger.info(f"Case {pv} acknowledged: {reason}")
            
            # Log CMS note for acknowledgment if CMS number is available
            if CMS_AVAILABLE and cms_number and notes:
                try:
                    # Create note text combining reason and notes
                    note_text = f"ACKNOWLEDGED: {reason}" if reason else "ACKNOWLEDGED"
                    if notes:
                        note_text += f" - {notes}"
                    
                    log_acknowledgment_note(cms_number, note_text)
                    logger.info(f"CMS acknowledgment note logged for PID {cms_number}")
                except Exception as cms_error:
                    logger.error(f"Failed to log CMS acknowledgment note: {cms_error}")
                    # Don't fail the acknowledgment if CMS logging fails
            
            return True
            
        except Exception as e:
            logger.error(f"Error acknowledging case {pv}: {e}")
            return False
    
    def unacknowledge_case(self, pv: str) -> bool:
        """Remove acknowledgment for a case"""
        try:
            pv = str(pv)
            if pv in self.acknowledged_cases:
                del self.acknowledged_cases[pv]
                self._save_acknowledgments()
                logger.info(f"Case {pv} unacknowledged")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unacknowledging case {pv}: {e}")
            return False
    
    def is_acknowledged(self, pv: str) -> bool:
        """Check if a case is currently acknowledged"""
        pv = str(pv)
        if pv not in self.acknowledged_cases:
            return False
        
        ack_data = self.acknowledged_cases[pv]
        
        # Check if snooze has expired
        if ack_data.get("review_after"):
            review_date = datetime.fromisoformat(ack_data["review_after"])
            if datetime.now() > review_date:
                # Auto-unacknowledge expired cases
                self.unacknowledge_case(pv)
                return False
        
        return True
    
    def get_acknowledgment_info(self, pv: str) -> Optional[Dict]:
        """Get acknowledgment details for a case"""
        pv = str(pv)
        if pv in self.acknowledged_cases:
            return self.acknowledged_cases[pv]
        return None
    
    def get_all_acknowledged(self) -> Dict:
        """Get all currently acknowledged cases"""
        # Clean up expired first
        self._cleanup_expired()
        return self.acknowledged_cases
    
    def _cleanup_expired(self):
        """Remove expired acknowledgments"""
        if not self.acknowledged_cases:
            return
            
        expired = []
        for pv, ack_data in self.acknowledged_cases.items():
            if ack_data.get("review_after"):
                try:
                    review_date = datetime.fromisoformat(ack_data["review_after"])
                    if datetime.now() > review_date:
                        expired.append(pv)
                except Exception as e:
                    logger.error(f"Error parsing review date for {pv}: {e}")
        
        for pv in expired:
            del self.acknowledged_cases[pv]
        
        if expired:
            self._save_acknowledgments()
            logger.info(f"Cleaned up {len(expired)} expired acknowledgments")
    
    def get_statistics(self) -> Dict:
        """Get acknowledgment statistics"""
        self._cleanup_expired()
        
        stats = {
            "total_acknowledged": len(self.acknowledged_cases),
            "by_reason": {},
            "by_status": {},
            "expiring_soon": 0
        }
        
        for pv, ack_data in self.acknowledged_cases.items():
            # Count by reason
            reason = ack_data.get("reason", "Unknown")
            stats["by_reason"][reason] = stats["by_reason"].get(reason, 0) + 1
            
            # Count by status
            status = ack_data.get("status", "Unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Count expiring soon (within 7 days)
            if ack_data.get("review_after"):
                review_date = datetime.fromisoformat(ack_data["review_after"])
                days_until = (review_date - datetime.now()).days
                if 0 < days_until <= 7:
                    stats["expiring_soon"] += 1
        
        return stats
    
    def bulk_acknowledge(self, pv_list: List[str], reason: str = "", 
                        snooze_days: int = 30) -> Dict:
        """Acknowledge multiple cases at once"""
        results = {
            "success": [],
            "failed": []
        }
        
        for pv in pv_list:
            if self.acknowledge_case(pv, reason=reason, snooze_days=snooze_days):
                results["success"].append(pv)
            else:
                results["failed"].append(pv)
        
        return results
    
    def get_cases_by_reason(self, reason: str) -> List[str]:
        """Get all cases acknowledged for a specific reason"""
        cases = []
        for pv, ack_data in self.acknowledged_cases.items():
            if ack_data.get("reason", "").upper() == reason.upper():
                cases.append(pv)
        return cases
    
    def extend_snooze(self, pv: str, additional_days: int) -> bool:
        """Extend the snooze period for an acknowledged case"""
        pv = str(pv)
        if pv not in self.acknowledged_cases:
            return False
        
        try:
            ack_data = self.acknowledged_cases[pv]
            if ack_data.get("review_after"):
                current_review = datetime.fromisoformat(ack_data["review_after"])
                new_review = current_review + timedelta(days=additional_days)
            else:
                new_review = datetime.now() + timedelta(days=additional_days)
            
            ack_data["review_after"] = new_review.isoformat()
            ack_data["snooze_days"] = ack_data.get("snooze_days", 0) + additional_days
            
            self._save_acknowledgments()
            logger.info(f"Extended snooze for case {pv} by {additional_days} days")
            return True
            
        except Exception as e:
            logger.error(f"Error extending snooze for case {pv}: {e}")
            return False
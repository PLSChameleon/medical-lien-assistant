#!/usr/bin/env python3
"""
Test script for incremental email cache updates
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.email_cache_service import EmailCacheService
from services.gmail_service import GmailService

def test_incremental_cache():
    """Test the incremental cache update functionality"""
    
    print("\n" + "="*60)
    print("EMAIL CACHE INCREMENTAL UPDATE TEST")
    print("="*60)
    
    try:
        # Initialize services
        print("\n📧 Initializing email cache service...")
        gmail_service = GmailService()
        cache_service = EmailCacheService(gmail_service=gmail_service)
        
        # Check current cache status
        print("\n📊 Current cache status:")
        stats = cache_service.get_cache_stats()
        print(f"   Status: {stats['status']}")
        print(f"   Email count: {stats['email_count']}")
        print(f"   Last updated: {stats['last_updated']}")
        print(f"   Last sync: {stats['last_sync']}")
        print(f"   Cache age: {stats['cache_age_days']} days")
        print(f"   Sync age: {stats['sync_age_days']} days")
        
        # Give user options
        print("\n" + "-"*40)
        print("OPTIONS:")
        print("1. Perform incremental update (fetch only new emails)")
        print("2. Force full sync (re-download all emails)")
        print("3. View cache statistics only")
        print("4. Clear cache and start fresh")
        print("-"*40)
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            # Incremental update
            print("\n🔄 Performing incremental update...")
            emails = cache_service.download_sent_emails(incremental=True)
            
            if emails:
                print(f"\n✅ Update complete! Total emails in cache: {len(emails)}")
                
                # Show updated stats
                stats = cache_service.get_cache_stats()
                print("\n📊 Updated cache statistics:")
                print(f"   Email count: {stats['email_count']}")
                print(f"   Last sync: {stats['last_sync']}")
                
        elif choice == "2":
            # Full sync
            limit = input("How many emails to fetch? (default 500): ").strip()
            limit = int(limit) if limit else 500
            
            print(f"\n⚡ Forcing full sync of {limit} emails...")
            emails = cache_service.force_full_sync(max_results=limit)
            
            if emails:
                print(f"\n✅ Full sync complete! Downloaded {len(emails)} emails")
                
        elif choice == "3":
            # Just show stats (already displayed above)
            print("\n✅ Cache statistics displayed above")
            
        elif choice == "4":
            # Clear cache
            confirm = input("\n⚠️  Are you sure you want to clear the cache? (y/N): ").strip().lower()
            if confirm == 'y':
                cache_service.cache = {"emails": [], "last_updated": None, "last_history_id": None, "last_sync_time": None}
                cache_service._save_cache()
                print("✅ Cache cleared successfully")
            else:
                print("❌ Cache clear cancelled")
        
        else:
            print("❌ Invalid option selected")
        
        # Ask if user wants to see cadence analysis
        if cache_service.cache.get('emails'):
            show_cadence = input("\n📊 Show cadence analysis? (y/N): ").strip().lower()
            if show_cadence == 'y':
                cache_service._display_cadence_summary()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_incremental_cache()
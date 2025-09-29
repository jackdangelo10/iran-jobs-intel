# tests/test_scrapers/test_irantalent.py
import uuid
import os
from src.database import IranJobsDB
from src.scrapers.irantalent.scraper import IranTalentScraper

def test_irantalent_full_session():
    """Run a full IranTalent scraping session for testing"""
    
    # Create test database
    os.makedirs("data/databases", exist_ok=True)
    test_db_path = "data/databases/test_irantalent_full.db"
    
    # Initialize database and scraper
    db = IranJobsDB(test_db_path)
    session_id = f"test_full_{uuid.uuid4().hex[:8]}"
    scraper = IranTalentScraper(db, session_id)
    
    print(f"Starting full IranTalent test session: {session_id}")
    print(f"Database will be saved to: {test_db_path}")
    
    try:
        # Run the complete scraping workflow
        results = scraper.run_scraping_session()
        
        print(f"\n=== Scraping Session Complete ===")
        print(f"Session ID: {session_id}")
        print(f"URLs discovered: {results['discovered']}")
        print(f"Jobs scraped: {results['scraped']}")
        print(f"Jobs failed: {results['failed']}")
        print(f"Database saved to: {test_db_path}")
        
    except Exception as e:
        print(f"❌ Scraping session failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()
        print(f"\n✅ Test complete! Open the database with your SQLite GUI:")
        print(f"   File: {test_db_path}")

if __name__ == "__main__":
    test_irantalent_full_session()
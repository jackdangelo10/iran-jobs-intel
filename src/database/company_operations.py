# database/company_operations.py
from __future__ import annotations

class CompanyOperations:

    def __init__(self, db_connection):
        self.db_connection = db_connection


    def track_company_discovery(self, company_url: str, source_site: str, session_id: str) -> None:
        """Track discovered company URL for later scraping"""
        # Check if already exists
        conn = self.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM company_tracking WHERE company_url = ?", (company_url,))
        
        if not cursor.fetchone():
            # Insert new company
            cursor.execute("""
                INSERT INTO company_tracking (company_url, source_site, first_seen_session, 
                                            last_seen_session, first_seen_date, last_seen_date)
                VALUES (?, ?, ?, ?, DATE('now'), DATE('now'))
            """, (company_url, source_site, session_id, session_id))
        else:
            # Update last seen
            cursor.execute("""
                UPDATE company_tracking 
                SET last_seen_session = ?, last_seen_date = DATE('now')
                WHERE company_url = ?
            """, (session_id, company_url))
        
        conn.commit()
        cursor.close()
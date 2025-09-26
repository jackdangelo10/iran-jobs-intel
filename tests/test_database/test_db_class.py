# tests/test_database/test_db_class.py


class TestIranJobsDB:

    def test_scrape_operations_available(self, in_memory_db):
        # Test that service classes are accessible
        assert hasattr(in_memory_db, 'scrapes')
        assert hasattr(in_memory_db, 'jobs')  # Note: you named this 'job' in your code
        assert hasattr(in_memory_db, 'companies')

    def test_database_initialization(self, in_memory_db):
        # Test that all tables were created
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        # Check that key tables exist
        assert 'raw_scrapes' in tables
        assert 'job_postings' in tables
        assert 'companies' in tables
        
    def test_scrape_operations_basic(self, in_memory_db):
        # Test basic scraping functionality
        scrape_id = in_memory_db.scrapes.save_raw_scrape(
            "irantalent", "test-url", "job_list", 
            "session-123", "<html>test</html>", 200
        )
        assert isinstance(scrape_id, int)
        assert scrape_id > 0
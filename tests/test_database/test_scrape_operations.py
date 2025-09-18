# tests/test_database/test_scrape_operations.py

class TestScrapeOperations:

    def test_save_raw_scrape(self, in_memory_db):
        # Test saving a new raw scrape
        scrape_id = in_memory_db.scrapes.save_raw_scrape(
            source_site="irantalent",
            source_url="http://example.com",
            page_type="job_list",
            scrape_session_id="session_1",
            raw_html="<html>Test Content</html>",
            response_status=200
        )
        assert isinstance(scrape_id, int) and scrape_id > 0

        # Test saving a duplicate raw scrape (should not store raw_html again)
        duplicate_scrape_id = in_memory_db.scrapes.save_raw_scrape(
            source_site="irantalent",
            source_url="http://example.com/duplicate",
            page_type="job_list",
            scrape_session_id="session_1",
            raw_html="<html>Test Content</html>",  # Same content as before
            response_status=200
        )
        assert isinstance(duplicate_scrape_id, int) and duplicate_scrape_id > 0
        assert duplicate_scrape_id != scrape_id  # Should be a different record

        # Verify that the duplicate record has empty raw_html
        conn = in_memory_db.db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT raw_html, is_duplicate FROM raw_scrapes WHERE id = ?", (duplicate_scrape_id,))
        result = cursor.fetchone()
        cursor.close()

        assert result is not None
        assert result[0] == ""  # raw_html should be empty for duplicate
        assert result[1] == 1   # is_duplicate should be True
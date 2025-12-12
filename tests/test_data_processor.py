import unittest
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_processing import (
    calculate_per_page_completion_rate,
    calculate_funnel_data,
    parse_log_data
)


class TestPageVisitDeduplication(unittest.TestCase):
    """Test that page visits are deduplicated correctly - keeping only first visit per user-page."""

    def create_test_page_visits(self):
        """Create test data with duplicate visits."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        data = {
            'user_id': ['user1', 'user1', 'user1', 'user2', 'user2', 'user3'],
            'path': ['/', '/', '/safety-check', '/', '/safety-check', '/'],
            'timestamp': [
                base_time,
                base_time + timedelta(hours=1),  # Duplicate visit by user1 to /
                base_time + timedelta(hours=2),
                base_time,
                base_time + timedelta(hours=1),
                base_time
            ],
            'event_type': ['page_visit'] * 6
        }

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week'] = df['timestamp'].dt.to_period('W')

        return df

    def test_funnel_data_deduplication(self):
        """Test that funnel data counts only first visit per user-page."""
        page_visits = self.create_test_page_visits()

        funnel_data = calculate_funnel_data(page_visits)

        # Check home page (/) - should have 3 unique visits (user1, user2, user3)
        # Even though user1 visited twice
        home_data = funnel_data[funnel_data['page'] == '/']
        self.assertEqual(len(home_data), 1)
        self.assertEqual(home_data.iloc[0]['total_visits'], 3)
        self.assertEqual(home_data.iloc[0]['unique_users'], 3)

        # Check safety-check page - should have 2 unique visits (user1, user2)
        safety_data = funnel_data[funnel_data['page'] == '/safety-check']
        self.assertEqual(len(safety_data), 1)
        self.assertEqual(safety_data.iloc[0]['total_visits'], 2)
        self.assertEqual(safety_data.iloc[0]['unique_users'], 2)

    def test_per_page_completion_deduplication(self):
        """Test that per-page completion counts only first visit per user-page."""
        page_visits = self.create_test_page_visits()

        per_page = calculate_per_page_completion_rate(page_visits)

        # Filter for home page
        home_data = per_page[per_page['page'] == '/']
        total_home_visits = home_data['total_visits'].sum()

        # Should be 3 total (user1, user2, user3) not 4 (even though user1 visited twice)
        self.assertEqual(total_home_visits, 3)

        # Filter for safety-check page
        safety_data = per_page[per_page['page'] == '/safety-check']
        total_safety_visits = safety_data['total_visits'].sum()

        # Should be 2 total (user1, user2)
        self.assertEqual(total_safety_visits, 2)

    def test_deduplication_keeps_first_visit(self):
        """Test that deduplication keeps the FIRST visit, not the last."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        # User visits same page in week 1 and week 2
        data = {
            'user_id': ['user1', 'user1'],
            'path': ['/', '/'],
            'timestamp': [
                base_time,  # Week 1
                base_time + timedelta(days=10)  # Week 2
            ],
            'event_type': ['page_visit', 'page_visit']
        }

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week'] = df['timestamp'].dt.to_period('W')

        per_page = calculate_per_page_completion_rate(df)

        # Should only have one entry (in week 1)
        home_data = per_page[per_page['page'] == '/']
        self.assertEqual(len(home_data), 1)

        # Should be in the first week
        first_week = str(df['week'].iloc[0])
        self.assertEqual(home_data.iloc[0]['week'], first_week)

    def test_multiple_users_same_page(self):
        """Test that different users visiting the same page are all counted."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        data = {
            'user_id': ['user1', 'user2', 'user3', 'user4'],
            'path': ['/', '/', '/', '/'],
            'timestamp': [base_time] * 4,
            'event_type': ['page_visit'] * 4
        }

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week'] = df['timestamp'].dt.to_period('W')

        funnel_data = calculate_funnel_data(df)

        home_data = funnel_data[funnel_data['page'] == '/']
        self.assertEqual(home_data.iloc[0]['total_visits'], 4)
        self.assertEqual(home_data.iloc[0]['unique_users'], 4)

    def test_same_user_different_pages(self):
        """Test that same user visiting different pages are all counted."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        data = {
            'user_id': ['user1', 'user1', 'user1'],
            'path': ['/', '/safety-check', '/confirmation'],
            'timestamp': [base_time, base_time + timedelta(minutes=5), base_time + timedelta(minutes=10)],
            'event_type': ['page_visit'] * 3
        }

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week'] = df['timestamp'].dt.to_period('W')

        funnel_data = calculate_funnel_data(df)

        # Each page should have 1 visit
        for page in ['/', '/safety-check', '/confirmation']:
            page_data = funnel_data[funnel_data['page'] == page]
            self.assertEqual(page_data.iloc[0]['total_visits'], 1)
            self.assertEqual(page_data.iloc[0]['unique_users'], 1)


class TestParseLogData(unittest.TestCase):
    """Test log data parsing."""

    def test_parse_basic_log_entry(self):
        """Test parsing a basic log entry."""
        data = {
            'Log': [
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=user123,path=/,method=GET,status_code=200'
            ]
        }
        df = pd.DataFrame(data)

        result = parse_log_data(df)

        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['event_type'], 'page_visit')
        self.assertEqual(result.iloc[0]['user_id'], 'user123')
        self.assertEqual(result.iloc[0]['path'], '/')

    def test_excludes_unknown_users(self):
        """Test that unknown/anonymous users are filtered out."""
        data = {
            'Log': [
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=user123,path=/',
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=unknown,path=/',
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=anonymous,path=/',
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=,path=/'
            ]
        }
        df = pd.DataFrame(data)

        result = parse_log_data(df)

        # Should only include user123
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['user_id'], 'user123')

    def test_excludes_asset_paths(self):
        """Test that asset paths are filtered out."""
        data = {
            'Log': [
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=user123,path=/',
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=user123,path=/assets/style.css',
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=user123,path=/images/logo.png',
                'timestamp=2024-01-01T10:00:00Z,event_type=page_visit,user_id=user123,path=/js/main.js'
            ]
        }
        df = pd.DataFrame(data)

        result = parse_log_data(df)

        # Should only include the root path
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]['path'], '/')


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_empty_dataframe(self):
        """Test handling of empty dataframe."""
        df = pd.DataFrame(columns=['user_id', 'path', 'timestamp', 'event_type'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        funnel_data = calculate_funnel_data(df)
        per_page = calculate_per_page_completion_rate(df)

        # Should return empty dataframes without errors
        self.assertTrue(funnel_data.empty)
        self.assertTrue(per_page.empty)

    def test_single_visit(self):
        """Test with a single visit."""
        base_time = datetime(2024, 1, 1, 10, 0, 0)

        data = {
            'user_id': ['user1'],
            'path': ['/'],
            'timestamp': [base_time],
            'event_type': ['page_visit']
        }

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['week'] = df['timestamp'].dt.to_period('W')

        funnel_data = calculate_funnel_data(df)

        home_data = funnel_data[funnel_data['page'] == '/']
        self.assertEqual(home_data.iloc[0]['total_visits'], 1)
        self.assertEqual(home_data.iloc[0]['unique_users'], 1)


if __name__ == '__main__':
    unittest.main()

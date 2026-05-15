"""
Tests for TikTokJobProcessor
Test-driven development approach
"""
import pytest
from unittest.mock import Mock, patch
from golike_core.api_client import GolikeAPIClient
from golike_core.logging import logger


class TestTikTokJobProcessor:
    """Test suite cho TikTokJobProcessor"""

    def test_processor_can_be_created(self):
        """Test: Processor có thể được khởi tạo"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        account_id = "test_account_123"

        # Act
        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, account_id)

        # Assert
        assert processor is not None
        assert processor.api_client == api_client
        assert processor.account_id == account_id

    def test_process_like_job_success(self):
        """Test: Process like job thành công"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        api_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "job_123",
                "type": "like",
                "link": "https://tiktok.com/@user/video/123",
                "object_id": "obj_123"
            }
        }
        api_client.post.return_value = {
            "status": 200,
            "data": {"prices": 10, "type": "like"}
        }

        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, "acc_123")

        # Act
        result = processor.process_job(["like"])

        # Assert
        assert result["success"] is True
        assert result["reward"] == 10
        api_client.get.assert_called_once()
        api_client.post.assert_called_once()

    def test_process_follow_job_success(self):
        """Test: Process follow job thành công"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        api_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "job_456",
                "type": "follow",
                "link": "https://tiktok.com/@user",
                "object_id": "obj_456"
            }
        }
        api_client.post.return_value = {
            "status": 200,
            "data": {"prices": 15, "type": "follow"}
        }

        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, "acc_123")

        # Act
        result = processor.process_job(["follow"])

        # Assert
        assert result["success"] is True
        assert result["reward"] == 15
        api_client.get.assert_called_once()
        api_client.post.assert_called_once()

    def test_process_job_no_available_jobs(self):
        """Test: Xử lý khi không có job available"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        api_client.get.return_value = {
            "status": 200,
            "data": None
        }

        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, "acc_123")

        # Act
        result = processor.process_job(["like"])

        # Assert
        assert result["success"] is False
        assert result["reason"] == "no_jobs"

    def test_process_job_complete_fails_with_retry(self):
        """Test: Retry khi complete job thất bại lần đầu"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        api_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "job_789",
                "type": "like",
                "link": "https://tiktok.com/@user/video/789",
                "object_id": "obj_789"
            }
        }
        # Lần đầu fail, lần 2 thành công
        api_client.post.side_effect = [
            {"status": 500, "message": "Server error"},
            {"status": 200, "data": {"prices": 10, "type": "like"}}
        ]

        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, "acc_123")

        # Act
        result = processor.process_job(["like"], retry_on_fail=True)

        # Assert
        assert result["success"] is True
        assert api_client.post.call_count == 2

    def test_process_job_skip_after_max_retries(self):
        """Test: Skip job sau khi retry tối đa"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        api_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "job_999",
                "type": "like",
                "link": "https://tiktok.com/@user/video/999",
                "object_id": "obj_999"
            }
        }
        # All post calls to complete_job fail (max 2 attempts when retry_on_fail=True)
        api_client.post.return_value = {"status": 500, "message": "Server error"}

        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, "acc_123")

        # Act
        result = processor.process_job(["like"], retry_on_fail=True)

        # Assert
        assert result["success"] is False
        assert result["reason"] == "max_retries_exceeded"

    def test_filter_job_by_type(self):
        """Test: Filter job theo type"""
        # Arrange
        api_client = Mock(spec=GolikeAPIClient)
        api_client.get.return_value = {
            "status": 200,
            "data": {
                "id": "job_111",
                "type": "follow",
                "link": "https://tiktok.com/@user",
                "object_id": "obj_111"
            }
        }

        from golike_tiktok.tiktok_client import TikTokJobProcessor
        processor = TikTokJobProcessor(api_client, "acc_123")

        # Act - Yêu cầu like nhưng job là follow
        result = processor.process_job(["like"])  # Only like jobs allowed

        # Assert
        assert result["success"] is False
        assert result["reason"] == "invalid_job_type"

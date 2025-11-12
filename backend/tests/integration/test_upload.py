"""
文件上传API集成测试 - T047
测试文件上传完整流程、多格式支持、验证逻辑和错误处理
"""

import pytest
import tempfile
import io
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

pytestmark = pytest.mark.integration


class TestFileUploadAPI:
    """文件上传API测试类"""

    @pytest.mark.asyncio
    async def test_upload_txt_file_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功上传TXT文件"""
        # 创建测试文件内容
        content = b"This is a test text file content.\nWith multiple lines."

        # 创建模拟文件
        files = {
            "file": ("test.txt", io.BytesIO(content), "text/plain")
        }

        # Mock存储客户端
        with patch("src.utils.storage.get_storage_client") as mock_storage:
            storage_client = AsyncMock()
            storage_client.upload_file.return_value = {
                "success": True,
                "bucket": "aicg-files",
                "object_key": "uploads/test-user-123/test.txt",
                "size": len(content),
                "etag": "test-etag-123",
                "url": "http://minio:9000/aicg-files/uploads/test-user-123/test.txt"
            }
            mock_storage.return_value = storage_client

            # 发送上传请求
            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files
            )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "文件上传成功"
        assert data["data"]["original_filename"] == "test.txt"
        assert data["data"]["file_type"] == "txt"
        assert data["data"]["file_size"] == len(content)

        # 验证存储客户端被正确调用
        storage_client.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_md_file_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功上传Markdown文件"""
        content = b"# Test Markdown\n\nThis is **bold** text."

        files = {
            "file": ("test.md", io.BytesIO(content), "text/markdown")
        }

        with patch("src.utils.storage.get_storage_client") as mock_storage:
            storage_client = AsyncMock()
            storage_client.upload_file.return_value = {
                "success": True,
                "object_key": "uploads/test-user-123/test.md",
                "size": len(content)
            }
            mock_storage.return_value = storage_client

            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["file_type"] == "md"

    @pytest.mark.asyncio
    async def test_upload_file_without_auth(self, client: AsyncClient):
        """测试未认证用户上传文件"""
        content = b"Test content"
        files = {
            "file": ("test.txt", io.BytesIO(content), "text/plain")
        }

        response = await client.post("/api/v1/files/upload", files=files)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_unsupported_file_type(self, client: AsyncClient, auth_headers: dict):
        """测试上传不支持的文件类型"""
        content = b"Test content"
        files = {
            "file": ("test.pdf", io.BytesIO(content), "application/pdf")
        }

        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "不支持的文件扩展名" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, client: AsyncClient, auth_headers: dict):
        """测试上传超大文件"""
        # 创建超过50MB的文件内容（模拟）
        content = b"x" * (50 * 1024 * 1024 + 1)  # 50MB + 1 byte

        files = {
            "file": ("large.txt", io.BytesIO(content), "text/plain")
        }

        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "文件大小超过限制" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client: AsyncClient, auth_headers: dict):
        """测试上传空文件"""
        content = b""
        files = {
            "file": ("empty.txt", io.BytesIO(content), "text/plain")
        }

        response = await client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files
        )

        assert response.status_code == 400
        assert "文件不能为空" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_storage_failure(self, client: AsyncClient, auth_headers: dict):
        """测试存储服务失败"""
        content = b"Test content"
        files = {
            "file": ("test.txt", io.BytesIO(content), "text/plain")
        }

        with patch("src.utils.storage.get_storage_client") as mock_storage:
            storage_client = AsyncMock()
            storage_client.upload_file.side_effect = Exception("Storage service unavailable")
            mock_storage.return_value = storage_client

            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files
            )

        assert response.status_code == 500
        assert "上传文件失败" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_file_type_mismatch_warning(self, client: AsyncClient, auth_headers: dict):
        """测试文件类型不匹配警告"""
        content = b"Test content"
        files = {
            "file": ("test.txt", io.BytesIO(content), "application/octet-stream")
        }

        with patch("src.utils.storage.get_storage_client") as mock_storage:
            storage_client = AsyncMock()
            storage_client.upload_file.return_value = {
                "success": True,
                "object_key": "uploads/test-user-123/test.txt",
                "size": len(content)
            }
            mock_storage.return_value = storage_client

            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files
            )

        # 应该仍然成功，但会有警告日志
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestFileManagementAPI:
    """文件管理API测试类"""

    @pytest.mark.asyncio
    async def test_get_storage_usage(self, client: AsyncClient, auth_headers: dict):
        """测试获取存储使用情况"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_project_statistics") as mock_stats:

            storage_client = AsyncMock()
            storage_client.list_files.return_value = [
                {
                    "object_key": "uploads/test-user-123/file1.txt",
                    "size": 1024,
                    "last_modified": "2025-01-01T00:00:00Z"
                },
                {
                    "object_key": "uploads/test-user-123/file2.md",
                    "size": 2048,
                    "last_modified": "2025-01-02T00:00:00Z"
                }
            ]
            mock_storage.return_value = storage_client

            mock_stats.return_value = {
                "total_projects": 2,
                "status_distribution": {"active": 2},
                "file_type_distribution": {"txt": 1, "md": 1}
            }

            response = await client.get(
                "/api/v1/files/storage/usage",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_files"] == 2
        assert data["total_size_mb"] == round((1024 + 2048) / (1024 * 1024), 2)
        assert "file_type_distribution" in data

    @pytest.mark.asyncio
    async def test_list_user_files(self, client: AsyncClient, auth_headers: dict):
        """测试列出用户文件"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_owner_projects") as mock_projects:

            storage_client = AsyncMock()
            storage_client.list_files.return_value = [
                {
                    "object_key": "uploads/test-user-123/file1.txt",
                    "size": 1024,
                    "last_modified": "2025-01-01T00:00:00Z"
                }
            ]
            mock_storage.return_value = storage_client

            mock_projects.return_value = ([], 0)  # 没有关联项目

            response = await client.get(
                "/api/v1/files/list",
                headers=auth_headers,
                params={"page": 1, "size": 10}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "file1.txt"
        assert data["files"][0]["is_orphaned"] is True

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files_dry_run(self, client: AsyncClient, auth_headers: dict):
        """测试清理孤立文件（试运行）"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_owner_projects") as mock_projects:

            storage_client = AsyncMock()
            storage_client.list_files.return_value = [
                {
                    "object_key": "uploads/test-user-123/orphaned.txt",
                    "size": 1024,
                    "last_modified": "2025-01-01T00:00:00Z"
                }
            ]
            mock_storage.return_value = storage_client

            mock_projects.return_value = ([], 0)  # 没有项目

            response = await client.delete(
                "/api/v1/files/cleanup/orphaned",
                headers=auth_headers,
                params={"dry_run": True, "older_than_days": 1}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["dry_run"] is True
        assert data["found_orphaned_files"] == 1
        assert data["deleted_files"] == 0

    @pytest.mark.asyncio
    async def test_batch_delete_files(self, client: AsyncClient, auth_headers: dict):
        """测试批量删除文件"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_owner_projects") as mock_projects:

            storage_client = AsyncMock()
            storage_client.delete_file.return_value = True
            mock_storage.return_value = storage_client

            mock_projects.return_value = ([], 0)  # 没有项目保护

            object_keys = ["uploads/test-user-123/file1.txt", "uploads/test-user-123/file2.md"]

            response = await client.post(
                "/api/v1/files/batch-delete",
                headers=auth_headers,
                json={"object_keys": object_keys}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["requested_files"] == 2
        assert data["deleted_files"] == 2
        assert len(data["deleted_keys"]) == 2

    @pytest.mark.asyncio
    async def test_batch_delete_protected_files(self, client: AsyncClient, auth_headers: dict):
        """测试批量删除受保护的文件"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_owner_projects") as mock_projects:

            storage_client = AsyncMock()
            mock_storage.return_value = storage_client

            # 模拟项目使用文件
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.file_path = "uploads/test-user-123/protected.txt"
            mock_projects.return_value = ([mock_project], 0)

            object_keys = ["uploads/test-user-123/protected.txt"]

            response = await client.post(
                "/api/v1/files/batch-delete",
                headers=auth_headers,
                json={"object_keys": object_keys}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["protected_files"] == 1
        assert data["deleted_files"] == 0

    @pytest.mark.asyncio
    async def test_check_file_integrity(self, client: AsyncClient, auth_headers: dict):
        """测试文件完整性检查"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_owner_projects") as mock_projects:

            storage_client = AsyncMock()
            storage_client.get_file_info.return_value = {
                "size": 1024,
                "metadata": {"file_hash": "test-hash-123"}
            }
            mock_storage.return_value = storage_client

            # 模拟项目
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.id = "project-123"
            mock_project.title = "Test Project"
            mock_project.file_path = "uploads/test-user-123/integrity.txt"
            mock_project.file_size = 1024
            mock_project.file_hash = "test-hash-123"
            mock_projects.return_value = ([mock_project], 0)

            response = await client.get(
                "/api/v1/files/integrity/check",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_checked"] == 1
        assert data["files_exist"] == 1
        assert data["integrity_score"] == 100.0

    @pytest.mark.asyncio
    async def test_check_specific_project_integrity(self, client: AsyncClient, auth_headers: dict):
        """测试检查特定项目的文件完整性"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_project_by_id") as mock_get_project:

            storage_client = AsyncMock()
            storage_client.get_file_info.return_value = None  # 文件不存在
            mock_storage.return_value = storage_client

            # 模拟项目
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.id = "project-123"
            mock_project.title = "Test Project"
            mock_project.file_path = "uploads/test-user-123/missing.txt"
            mock_get_project.return_value = mock_project

            response = await client.get(
                "/api/v1/files/integrity/check",
                headers=auth_headers,
                params={"project_id": "project-123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "project-123"
        assert data["files_missing"] == 1
        assert data["integrity_score"] == -100.0


class TestFileUploadEdgeCases:
    """文件上传边界情况测试"""

    @pytest.mark.asyncio
    async def test_upload_filename_with_special_chars(self, client: AsyncClient, auth_headers: dict):
        """测试上传包含特殊字符的文件名"""
        content = b"Test content"
        files = {
            "file": ("test file (1).txt", io.BytesIO(content), "text/plain")
        }

        with patch("src.utils.storage.get_storage_client") as mock_storage:
            storage_client = AsyncMock()
            storage_client.upload_file.return_value = {
                "success": True,
                "object_key": "uploads/test-user-123/test-file-1.txt",
                "size": len(content)
            }
            mock_storage.return_value = storage_client

            response = await client.post(
                "/api/v1/files/upload",
                headers=auth_headers,
                files=files
            )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["original_filename"] == "test file (1).txt"

    @pytest.mark.asyncio
    async def test_batch_delete_too_many_files(self, client: AsyncClient, auth_headers: dict):
        """测试批量删除过多文件"""
        object_keys = [f"uploads/test-user-123/file{i}.txt" for i in range(101)]

        response = await client.post(
            "/api/v1/files/batch-delete",
            headers=auth_headers,
            json={"object_keys": object_keys}
        )

        assert response.status_code == 400
        assert "单次批量删除文件数量不能超过100个" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_delete_empty_list(self, client: AsyncClient, auth_headers: dict):
        """测试批量删除空列表"""
        response = await client.post(
            "/api/v1/files/batch-delete",
            headers=auth_headers,
            json={"object_keys": []}
        )

        assert response.status_code == 400
        assert "文件对象键列表不能为空" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_files_pagination(self, client: AsyncClient, auth_headers: dict):
        """测试文件列表分页"""
        with patch("src.utils.storage.get_storage_client") as mock_storage, \
             patch("src.services.project.ProjectService.get_owner_projects") as mock_projects:

            storage_client = AsyncMock()
            storage_client.list_files.return_value = [
                {"object_key": f"uploads/test-user-123/file{i}.txt", "size": 1024}
                for i in range(25)
            ]
            mock_storage.return_value = storage_client
            mock_projects.return_value = ([], 0)

            response = await client.get(
                "/api/v1/files/list",
                headers=auth_headers,
                params={"page": 1, "size": 10}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["files"]) == 10
        assert data["page"] == 1
        assert data["size"] == 10
        assert data["total_pages"] == 3
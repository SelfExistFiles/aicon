"""
项目管理API集成测试 - T048
测试项目CRUD操作、分页搜索、归档功能和权限控制
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone

pytestmark = pytest.mark.integration


class TestProjectCRUD:
    """项目CRUD操作测试类"""

    @pytest.mark.asyncio
    async def test_create_project_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功创建项目"""
        project_data = {
            "title": "测试项目",
            "description": "这是一个测试项目描述",
            "file_name": "test.txt",
            "file_size": 1024,
            "file_type": "txt",
            "file_path": "uploads/test-user-123/test.txt",
            "file_hash": "abc123def456"
        }

        with patch("src.services.project.ProjectService.create_project") as mock_create:
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.to_dict.return_value = {
                "id": "project-123",
                "owner_id": "test-user-123",
                "title": "测试项目",
                "description": "这是一个测试项目描述",
                "file_name": "test.txt",
                "file_size": 1024,
                "file_type": "txt",
                "file_path": "uploads/test-user-123/test.txt",
                "file_hash": "abc123def456",
                "word_count": 0,
                "chapter_count": 0,
                "paragraph_count": 0,
                "sentence_count": 0,
                "status": "active",
                "processing_progress": 0,
                "error_message": None,
                "generation_settings": None,
                "completed_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            mock_create.return_value = mock_project

            response = await client.post(
                "/api/v1/projects/",
                headers=auth_headers,
                json=project_data
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "测试项目"
        assert data["description"] == "这是一个测试项目描述"
        assert data["file_type"] == "txt"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_project_minimal_data(self, client: AsyncClient, auth_headers: dict):
        """测试使用最小数据创建项目"""
        project_data = {
            "title": "最小测试项目"
        }

        with patch("src.services.project.ProjectService.create_project") as mock_create:
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.to_dict.return_value = {
                "id": "project-456",
                "owner_id": "test-user-123",
                "title": "最小测试项目",
                "description": None,
                "file_name": "",
                "file_size": 0,
                "file_type": "",
                "file_path": "",
                "file_hash": None,
                "word_count": 0,
                "chapter_count": 0,
                "paragraph_count": 0,
                "sentence_count": 0,
                "status": "active",
                "processing_progress": 0,
                "error_message": None,
                "generation_settings": None,
                "completed_at": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            mock_create.return_value = mock_project

            response = await client.post(
                "/api/v1/projects/",
                headers=auth_headers,
                json=project_data
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "最小测试项目"
        assert data["description"] is None

    @pytest.mark.asyncio
    async def test_create_project_invalid_title(self, client: AsyncClient, auth_headers: dict):
        """测试创建项目时标题无效"""
        project_data = {
            "title": "",  # 空标题
            "description": "测试描述"
        }

        response = await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json=project_data
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_create_project_without_auth(self, client: AsyncClient):
        """测试未认证用户创建项目"""
        project_data = {
            "title": "测试项目"
        }

        response = await client.post("/api/v1/projects/", json=project_data)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_project_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功获取项目详情"""
        project_id = "project-123"

        with patch("src.services.project.ProjectService.get_project_by_id") as mock_get:
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.to_dict.return_value = {
                "id": project_id,
                "owner_id": "test-user-123",
                "title": "测试项目",
                "description": "测试描述",
                "file_name": "test.txt",
                "file_size": 1024,
                "file_type": "txt",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            mock_get.return_value = mock_project

            response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project_id
        assert data["title"] == "测试项目"

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在的项目"""
        project_id = "nonexistent-project"

        with patch("src.services.project.ProjectService.get_project_by_id") as mock_get:
            mock_get.return_value = None

            response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers
            )

        assert response.status_code == 404
        assert "项目不存在" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_project_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功更新项目"""
        project_id = "project-123"
        update_data = {
            "title": "更新后的标题",
            "description": "更新后的描述"
        }

        with patch("src.services.project.ProjectService.update_project") as mock_update:
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.to_dict.return_value = {
                "id": project_id,
                "owner_id": "test-user-123",
                "title": "更新后的标题",
                "description": "更新后的描述",
                "file_name": "test.txt",
                "file_size": 1024,
                "file_type": "txt",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            mock_update.return_value = mock_project

            response = await client.put(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers,
                json=update_data
            )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "更新后的标题"
        assert data["description"] == "更新后的描述"

    @pytest.mark.asyncio
    async def test_update_project_no_fields(self, client: AsyncClient, auth_headers: dict):
        """测试更新项目时没有提供字段"""
        project_id = "project-123"
        update_data = {}

        response = await client.put(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers,
            json=update_data
        )

        assert response.status_code == 400
        assert "没有提供更新字段" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试更新不存在的项目"""
        project_id = "nonexistent-project"
        update_data = {
            "title": "更新后的标题"
        }

        with patch("src.services.project.ProjectService.update_project") as mock_update:
            mock_update.return_value = None

            response = await client.put(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers,
                json=update_data
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_project_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功删除项目"""
        project_id = "project-123"

        with patch("src.services.project.ProjectService.delete_project") as mock_delete:
            mock_delete.return_value = True

            response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["project_id"] == project_id

    @pytest.mark.asyncio
    async def test_delete_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试删除不存在的项目"""
        project_id = "nonexistent-project"

        with patch("src.services.project.ProjectService.delete_project") as mock_delete:
            mock_delete.return_value = False

            response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers
            )

        assert response.status_code == 404


class TestProjectArchive:
    """项目归档功能测试类"""

    @pytest.mark.asyncio
    async def test_archive_project_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功归档项目"""
        project_id = "project-123"

        with patch("src.services.project.ProjectService.archive_project") as mock_archive:
            from unittest.mock import Mock
            mock_project = Mock()
            mock_project.to_dict.return_value = {
                "id": project_id,
                "owner_id": "test-user-123",
                "title": "测试项目",
                "status": "archived",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            mock_archive.return_value = mock_project

            response = await client.put(
                f"/api/v1/projects/{project_id}/archive",
                headers=auth_headers
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

    @pytest.mark.asyncio
    async def test_archive_project_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试归档不存在的项目"""
        project_id = "nonexistent-project"

        with patch("src.services.project.ProjectService.archive_project") as mock_archive:
            mock_archive.return_value = None

            response = await client.put(
                f"/api/v1/projects/{project_id}/archive",
                headers=auth_headers
            )

        assert response.status_code == 404


class TestProjectListAndSearch:
    """项目列表和搜索功能测试类"""

    @pytest.mark.asyncio
    async def test_get_projects_list(self, client: AsyncClient, auth_headers: dict):
        """测试获取项目列表"""
        with patch("src.services.project.ProjectService.get_owner_projects") as mock_get_projects:
            from unittest.mock import Mock
            mock_project1 = Mock()
            mock_project1.to_dict.return_value = {
                "id": "project-1",
                "title": "项目1",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            mock_project2 = Mock()
            mock_project2.to_dict.return_value = {
                "id": "project-2",
                "title": "项目2",
                "status": "active",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            mock_get_projects.return_value = ([mock_project1, mock_project2], 2)

            response = await client.get(
                "/api/v1/projects/",
                headers=auth_headers,
                params={"page": 1, "size": 20}
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["projects"]) == 2
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["size"] == 20
        assert data["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_get_projects_with_status_filter(self, client: AsyncClient, auth_headers: dict):
        """测试使用状态过滤获取项目列表"""
        with patch("src.services.project.ProjectService.get_owner_projects") as mock_get_projects:
            mock_get_projects.return_value = ([], 0)

            response = await client.get(
                "/api/v1/projects/",
                headers=auth_headers,
                params={"project_status": "active"}
            )

        assert response.status_code == 200
        # 验证状态过滤参数被正确传递

    @pytest.mark.asyncio
    async def test_get_projects_with_search(self, client: AsyncClient, auth_headers: dict):
        """测试使用搜索关键词获取项目列表"""
        with patch("src.services.project.ProjectService.get_owner_projects") as mock_get_projects:
            mock_get_projects.return_value = ([], 0)

            response = await client.get(
                "/api/v1/projects/",
                headers=auth_headers,
                params={"search": "测试关键词"}
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_projects_with_sorting(self, client: AsyncClient, auth_headers: dict):
        """测试使用排序获取项目列表"""
        with patch("src.services.project.ProjectService.get_owner_projects") as mock_get_projects:
            mock_get_projects.return_value = ([], 0)

            response = await client.get(
                "/api/v1/projects/",
                headers=auth_headers,
                params={"sort_by": "title", "sort_order": "asc"}
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_projects_pagination(self, client: AsyncClient, auth_headers: dict):
        """测试项目列表分页"""
        with patch("src.services.project.ProjectService.get_owner_projects") as mock_get_projects:
            mock_get_projects.return_value = ([], 0)

            response = await client.get(
                "/api/v1/projects/",
                headers=auth_headers,
                params={"page": 2, "size": 10}
            )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_projects_invalid_page(self, client: AsyncClient, auth_headers: dict):
        """测试无效的页码"""
        response = await client.get(
            "/api/v1/projects/",
            headers=auth_headers,
            params={"page": 0}  # 页码必须 >= 1
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_projects_invalid_size(self, client: AsyncClient, auth_headers: dict):
        """测试无效的页面大小"""
        response = await client.get(
            "/api/v1/projects/",
            headers=auth_headers,
            params={"size": 0}  # 大小必须 >= 1
        )

        assert response.status_code == 422

        response = await client.get(
            "/api/v1/projects/",
            headers=auth_headers,
            params={"size": 200}  # 大小必须 <= 100
        )

        assert response.status_code == 422


class TestProjectPermissions:
    """项目权限控制测试类"""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_project(self, client: AsyncClient, auth_headers: dict):
        """测试用户无法访问其他用户的项目"""
        project_id = "other-user-project"

        with patch("src.services.project.ProjectService.get_project_by_id") as mock_get:
            # 返回None表示用户无权访问
            mock_get.return_value = None

            response = await client.get(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_update_other_user_project(self, client: AsyncClient, auth_headers: dict):
        """测试用户无法更新其他用户的项目"""
        project_id = "other-user-project"
        update_data = {"title": "恶意更新"}

        with patch("src.services.project.ProjectService.update_project") as mock_update:
            mock_update.return_value = None

            response = await client.put(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers,
                json=update_data
            )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_user_cannot_delete_other_user_project(self, client: AsyncClient, auth_headers: dict):
        """测试用户无法删除其他用户的项目"""
        project_id = "other-user-project"

        with patch("src.services.project.ProjectService.delete_project") as mock_delete:
            mock_delete.return_value = False

            response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers=auth_headers
            )

        assert response.status_code == 404


class TestProjectValidationError:
    """项目验证错误测试类"""

    @pytest.mark.asyncio
    async def test_create_project_invalid_file_type(self, client: AsyncClient, auth_headers: dict):
        """测试创建项目时文件类型无效"""
        project_data = {
            "title": "测试项目",
            "file_type": "invalid_type"  # 不在允许的类型列表中
        }

        response = await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json=project_data
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_project_title_too_long(self, client: AsyncClient, auth_headers: dict):
        """测试创建项目时标题过长"""
        project_data = {
            "title": "x" * 201,  # 超过200字符限制
            "description": "测试描述"
        }

        response = await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json=project_data
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_project_description_too_long(self, client: AsyncClient, auth_headers: dict):
        """测试创建项目时描述过长"""
        project_data = {
            "title": "测试项目",
            "description": "x" * 1001  # 超过1000字符限制
        }

        response = await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json=project_data
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_project_negative_file_size(self, client: AsyncClient, auth_headers: dict):
        """测试创建项目时文件大小为负数"""
        project_data = {
            "title": "测试项目",
            "file_size": -100  # 负数文件大小
        }

        response = await client.post(
            "/api/v1/projects/",
            headers=auth_headers,
            json=project_data
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_sort_order(self, client: AsyncClient, auth_headers: dict):
        """测试无效的排序顺序"""
        response = await client.get(
            "/api/v1/projects/",
            headers=auth_headers,
            params={"sort_order": "invalid"}  # 不是 asc 或 desc
        )

        assert response.status_code == 422


class TestProjectServiceError:
    """项目服务错误测试类"""

    @pytest.mark.asyncio
    async def test_project_service_error_on_create(self, client: AsyncClient, auth_headers: dict):
        """测试创建项目时服务错误"""
        project_data = {
            "title": "测试项目"
        }

        with patch("src.services.project.ProjectService.create_project") as mock_create:
            from src.services.project import ProjectServiceError
            mock_create.side_effect = ProjectServiceError("Database connection failed")

            response = await client.post(
                "/api/v1/projects/",
                headers=auth_headers,
                json=project_data
            )

        assert response.status_code == 500
        assert "创建项目失败" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_project_service_error_on_list(self, client: AsyncClient, auth_headers: dict):
        """测试获取项目列表时服务错误"""
        with patch("src.services.project.ProjectService.get_owner_projects") as mock_get:
            from src.services.project import ProjectServiceError
            mock_get.side_effect = ProjectServiceError("Database query failed")

            response = await client.get(
                "/api/v1/projects/",
                headers=auth_headers
            )

        assert response.status_code == 500
        assert "获取项目列表失败" in response.json()["detail"]
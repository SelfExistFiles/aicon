import asyncio
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_key import APIKey
from src.models.movie import MediaType, MovieGenerationHistory
from src.models.user import User
from src.services.api_key import APIKeyService


@pytest.mark.integration
class TestAPIKeyDeletion:
    def test_delete_api_key_clears_generation_history_reference(
        self, db_session: AsyncSession
    ):
        async def run_test():
            user = User(
                username=f"user-{uuid.uuid4().hex[:8]}",
                email=f"{uuid.uuid4().hex[:8]}@example.com",
                password_hash="hashed-password",
            )
            db_session.add(user)
            await db_session.flush()

            api_key = APIKey(
                user_id=user.id,
                provider="openai",
                name="test key",
            )
            api_key.set_api_key("secret-key")
            db_session.add(api_key)
            await db_session.flush()

            history = MovieGenerationHistory(
                resource_type="scene_image",
                resource_id=uuid.uuid4(),
                media_type=MediaType.IMAGE.value,
                result_url="https://example.com/image.png",
                prompt="test prompt",
                model="gpt-image-1",
                api_key_id=api_key.id,
                is_selected=False,
            )
            db_session.add(history)
            await db_session.commit()

            service = APIKeyService(db_session)
            await service.delete_api_key(str(api_key.id), str(user.id))
            await db_session.commit()

            deleted_key = await db_session.get(APIKey, api_key.id)
            assert deleted_key is None

            refreshed_history = await db_session.scalar(
                select(MovieGenerationHistory).where(MovieGenerationHistory.id == history.id)
            )
            assert refreshed_history is not None
            assert refreshed_history.api_key_id is None

        asyncio.run(run_test())

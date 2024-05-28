import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_get_choices_200(async_client: AsyncClient):
    assert False

import uuid
import pytest
from fastapi import HTTPException

from backend.deps import get_org_id


def test_get_org_id_valid():
    uid = uuid.uuid4()
    assert get_org_id(str(uid)) == uid


def test_get_org_id_missing():
    with pytest.raises(HTTPException) as exc:
        get_org_id(None)  # type: ignore[arg-type]
    assert exc.value.status_code == 400


def test_get_org_id_invalid():
    with pytest.raises(HTTPException):
        get_org_id("not-a-uuid") 
"""Every test writes .env changes and expiry dates to a temporary folder, never to the real backend/.env."""
import pytest

import envfile
import expiry_dates


@pytest.fixture(autouse=True)
def private_files(tmp_path, monkeypatch):
    monkeypatch.setattr(envfile, "ENV", tmp_path / "test.env")
    monkeypatch.setattr(expiry_dates, "FILE", tmp_path / "expiry.json")

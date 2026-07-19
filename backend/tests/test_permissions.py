from __future__ import annotations

import os
import stat

import pytest


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes only")
def test_local_database_uses_private_file_modes(database, settings):
    with database.connect() as conn:
        conn.execute("SELECT 1").fetchone()

    assert stat.S_IMODE(settings.data_dir.stat().st_mode) == 0o700
    assert stat.S_IMODE(settings.database_path.stat().st_mode) == 0o600

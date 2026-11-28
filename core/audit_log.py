"""Ghi nhat ky nghiep vu tu ung dung vao CSDL dung chung."""

import json


def _json_value(value):
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def write_audit_log(
    cursor,
    table_name,
    action,
    record_key,
    before=None,
    after=None,
):
    """Ghi mot su kien sau khi nghiep vu da duoc kiem tra, trong transaction hien tai."""
    cursor.execute(
        """
        INSERT INTO dbo.NHAT_KY_THAY_DOI
            (TAIKHOAN_SQL, BANG_TAC_DONG, HANH_DONG,
             KHOA_DULIEU, DU_LIEU_TRUOC, DU_LIEU_SAU)
        VALUES
            (ORIGINAL_LOGIN(), ?, ?, ?, ?, ?)
        """,
        str(table_name)[:128],
        str(action).upper()[:10],
        _json_value(record_key),
        _json_value(before),
        _json_value(after),
    )

"""Repository SQL cho tác giả, thể loại, nhà xuất bản và thương hiệu."""

from core.catalog_config import CATALOGS
from core.sql_support import resolve_connection


class CatalogRepository:
    """Thực hiện truy vấn CRUD cho một loại danh mục được cấu hình sẵn."""

    def __init__(self, connection_source, catalog_type):
        if catalog_type not in CATALOGS:
            raise ValueError(f"Loại danh mục không hợp lệ: {catalog_type}")
        self.connection_source = connection_source
        self.config = CATALOGS[catalog_type]

    def list_records(self, keyword=""):
        """Lấy các bản ghi chưa xóa mềm, hỗ trợ tìm trên các cột đã cấu hình."""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            base_sql, order_by = self.config["select_sql"].rsplit(" ORDER BY ", 1)
            keyword = str(keyword or "").strip()
            params = []
            if keyword:
                conditions = []
                for column in self.config["search_columns"]:
                    conditions.append(
                        f"CONVERT(NVARCHAR(4000), {column}) LIKE ?"
                    )
                    params.append(f"%{keyword}%")
                sql = base_sql + " AND (" + " OR ".join(conditions) + ") ORDER BY " + order_by
                cursor.execute(sql, *params)
            else:
                cursor.execute(self.config["select_sql"])
            columns = [field[0] for field in self.config["fields"]]
            return [
                {column: value for column, value in zip(columns, row)}
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()

    def _next_code(self, cursor, lock_table=False):
        """Sinh mã từ hậu tố lớn nhất, tính cả bản ghi đã xóa mềm."""
        config = self.config
        prefix = config["code_prefix"]
        id_column = config["id_column"]
        table = config["table"]
        table_hint = " WITH (TABLOCKX, HOLDLOCK)" if lock_table else ""
        prefix_len = len(prefix)
        sql = f"""
            SELECT COALESCE(
                MAX(TRY_CONVERT(BIGINT, SUBSTRING({id_column}, {prefix_len + 1}, 20))),
                0
            )
            FROM dbo.{table}{table_hint}
            WHERE UPPER(LEFT({id_column}, {prefix_len})) = ?
              AND TRY_CONVERT(BIGINT, SUBSTRING({id_column}, {prefix_len + 1}, 20)) IS NOT NULL
        """
        cursor.execute(sql, prefix)
        number = int(cursor.fetchone()[0] or 0) + 1
        code = f"{prefix}{number:03d}"
        if len(code) > 20:
            raise ValueError(f"Mã {id_column} vượt quá 20 ký tự.")
        return code

    def preview_next_code(self):
        """Đọc mã dự kiến để hiển thị; mã thật được sinh lại trong transaction thêm."""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            code = self._next_code(cursor)
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def create_record(self, values):
        """Sinh mã dưới khóa bảng rồi thêm bản ghi trong cùng transaction."""
        config = self.config
        values = list(values or [])
        if len(values) != len(config["fields"]):
            raise ValueError("Dữ liệu danh mục không đúng cấu trúc.")

        normalized = []
        missing = []
        id_index = None
        for index, (column, label, _placeholder, max_length, required) in enumerate(config["fields"]):
            if column == config["id_column"]:
                id_index = index
            value = str(values[index] or "").strip()
            if len(value) > max_length:
                raise ValueError(f"{label.replace(':', '')} vượt quá {max_length} ký tự.")
            if required and column != config["id_column"] and not value:
                missing.append(label.replace(":", ""))
            normalized.append(value or None)
        if missing:
            raise ValueError("Vui lòng nhập: " + ", ".join(missing))
        if id_index is None:
            raise RuntimeError("Cấu hình danh mục thiếu cột mã.")

        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            code = self._next_code(cursor, lock_table=True)
            normalized[id_index] = code
            cursor.execute(config["insert_sql"], *normalized)
            conn.commit()
            return code
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def update_record(self, record_id, values):
        """Cập nhật một bản ghi đang hoạt động; trả False nếu không có bản ghi."""
        config = self.config
        values = list(values or [])
        editable_fields = [
            field for field in config["fields"]
            if field[0] != config["id_column"]
        ]
        if len(values) != len(editable_fields):
            raise ValueError("Dữ liệu cập nhật danh mục không đúng cấu trúc.")

        normalized = []
        missing = []
        for value, field in zip(values, editable_fields):
            _column, label, _placeholder, max_length, required = field
            value = str(value or "").strip()
            if len(value) > max_length:
                raise ValueError(f"{label.replace(':', '')} vượt quá {max_length} ký tự.")
            if required and not value:
                missing.append(label.replace(":", ""))
            normalized.append(value or None)
        if missing:
            raise ValueError("Vui lòng nhập: " + ", ".join(missing))

        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute(config["update_sql"], *normalized, record_id)
            changed = cursor.rowcount != 0
            if changed:
                conn.commit()
            else:
                conn.rollback()
            return changed
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def soft_delete(self, record_id):
        """Đánh dấu xóa mềm; không xóa vật lý dữ liệu lịch sử."""
        conn = resolve_connection(self.connection_source)
        cursor = conn.cursor()
        try:
            cursor.execute(self.config["delete_sql"], record_id)
            changed = cursor.rowcount != 0
            if changed:
                conn.commit()
            else:
                conn.rollback()
            return changed
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

"""Service nghiệp vụ cho các danh mục sản phẩm."""

from core.danh_muc.repository import CatalogRepository


class CatalogService:
    """Cung cấp API nghiệp vụ độc lập giao diện cho nhóm danh mục."""

    def __init__(self, repository):
        if not isinstance(repository, CatalogRepository):
            raise TypeError("repository phải là CatalogRepository.")
        self.repository = repository

    def list_records(self, keyword=""):
        return self.repository.list_records(keyword)

    def preview_next_code(self):
        return self.repository.preview_next_code()

    def create_record(self, values):
        return self.repository.create_record(values)

    def update_record(self, record_id, values):
        if not str(record_id or "").strip():
            raise ValueError("Mã danh mục không hợp lệ.")
        return self.repository.update_record(record_id, values)

    def soft_delete(self, record_id):
        if not str(record_id or "").strip():
            raise ValueError("Mã danh mục không hợp lệ.")
        return self.repository.soft_delete(record_id)

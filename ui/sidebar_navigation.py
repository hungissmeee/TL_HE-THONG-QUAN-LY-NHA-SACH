"""Mixin điều hướng sidebar và các trang chức năng của cửa sổ chính."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QToolButton, QVBoxLayout, QWidget

from ui.permissions import allowed_pages_for_user


class SidebarNavigationMixin:
    """Tập trung cấu hình nhóm menu, nút điều hướng và quyền hiển thị trang."""

    def _create_sidebar_groups(self):
        """Tạo các nhóm menu theo cấu hình khai báo trong sidebar_group_config."""
        for group in self.sidebar_group_config:
            group_key = group["key"]
            expanded = bool(group.get("expanded", False))

            header = QToolButton()
            header.setObjectName("navGroupButton")
            header.setText(group["title"])
            header.setCheckable(True)
            header.setChecked(expanded)
            header.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            header.setArrowType(
                Qt.ArrowType.DownArrow if expanded
                else Qt.ArrowType.RightArrow
            )

            content = QWidget()
            content.setObjectName(f"navGroupContent_{group_key}")
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(3)
            content.setVisible(expanded)

            self.nav_groups_layout.addWidget(header)
            self.nav_groups_layout.addWidget(content)

            self.nav_group_widgets[group_key] = {
                "header": header,
                "content": content,
                "layout": content_layout,
                "pages": list(group["pages"]),
            }
            self.nav_group_state[group_key] = expanded

            for page_key in group["pages"]:
                self.danh_sach_to_group[page_key] = group_key

            header.toggled.connect(
                lambda checked, key=group_key:
                self.toggle_nav_group(key, checked)
            )

    def toggle_nav_group(self, group_key, expanded):
        """Mở hoặc thu gọn nội dung của một nhóm menu."""
        group = self.nav_group_widgets.get(group_key)
        if group is None:
            return

        self.nav_group_state[group_key] = bool(expanded)
        group["header"].setArrowType(
            Qt.ArrowType.DownArrow if expanded
            else Qt.ArrowType.RightArrow
        )
        group["content"].setVisible(
            bool(expanded) and group["header"].isVisible()
        )

    def _refresh_sidebar_groups(self):
        """Ẩn nhóm menu không còn trang nào được phép hiển thị."""
        for group_key, group in self.nav_group_widgets.items():
            # isHidden() kiểm tra trạng thái ẩn trực tiếp của từng nút,
            # không bị ảnh hưởng bởi việc nhóm cha đang thu gọn.
            has_visible_page = any(
                key in self.nav_buttons
                and not self.nav_buttons[key].isHidden()
                for key in group["pages"]
            )

            group["header"].setVisible(has_visible_page)
            group["content"].setVisible(
                has_visible_page and self.nav_group_state[group_key]
            )

    # ==================================================
    # THÊM TRANG VÀO HỆ THỐNG
    # ==================================================

    def add_page(self, key, title, page):
        """Đăng ký trang vào QStackedWidget và tạo nút điều hướng tương ứng."""
        self.danh_sachs[key] = page
        self.danh_sach_titles[key] = title
        self.stack.addWidget(page)

        button = QPushButton(title)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.clicked.connect(
            lambda checked=False, k=key: self.show_page(k)
        )

        group_key = self.danh_sach_to_group.get(key)
        if group_key not in self.nav_group_widgets:
            # Trang chưa được khai báo nhóm sẽ tự đưa vào nhóm Khác.
            group_key = self._ensure_other_group()
            self.danh_sach_to_group[key] = group_key

        group_pages = self.nav_group_widgets[group_key]["pages"]
        if key not in group_pages:
            group_pages.append(key)

        self.nav_group_widgets[group_key]["layout"].addWidget(button)
        self.nav_buttons[key] = button

    def _ensure_other_group(self):
        """Tạo nhóm Khác khi một trang chưa được khai báo trong cấu hình menu."""
        group_key = "other"
        if group_key not in self.nav_group_widgets:
            group = {
                "key": group_key,
                "title": "KHÁC",
                "pages": [],
                "expanded": True,
            }
            self.sidebar_group_config.append(group)

            header = QToolButton()
            header.setObjectName("navGroupButton")
            header.setText(group["title"])
            header.setCheckable(True)
            header.setChecked(True)
            header.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
            header.setArrowType(Qt.ArrowType.DownArrow)

            content = QWidget()
            content_layout = QVBoxLayout(content)
            content_layout.setContentsMargins(0, 0, 0, 0)
            content_layout.setSpacing(3)

            self.nav_groups_layout.insertWidget(
                self.nav_groups_layout.count() - 1, header
            )
            self.nav_groups_layout.insertWidget(
                self.nav_groups_layout.count() - 1, content
            )

            self.nav_group_widgets[group_key] = {
                "header": header,
                "content": content,
                "layout": content_layout,
                "pages": group["pages"],
            }
            self.nav_group_state[group_key] = True
            header.toggled.connect(
                lambda checked, key=group_key:
                self.toggle_nav_group(key, checked)
            )

        return group_key

    # ==================================================
    # CHUYỂN TRANG
    # ==================================================

    def show_page(self, key):
        """Chuyển sang trang được chọn, làm mới dữ liệu và cập nhật trạng thái nút điều hướng."""
        if key not in self.danh_sachs:
            return

        self.stack.setCurrentWidget(self.danh_sachs[key])
        self.danh_sach_title.setText(self.danh_sach_titles[key])

        # Tự mở nhóm chứa trang hiện tại nếu nhóm đang thu gọn.
        group_key = self.danh_sach_to_group.get(key)
        if group_key in self.nav_group_widgets:
            if not self.nav_group_state.get(group_key, False):
                self.nav_group_widgets[group_key]["header"].setChecked(True)
                self.toggle_nav_group(group_key, True)

        self._refresh_page_data(self.danh_sachs[key])

        for page_key, button in self.nav_buttons.items():
            button.setChecked(page_key == key)

    @staticmethod

    def apply_role_navigation(self):
        """Áp dụng danh sách trang được phép dựa trên vai trò nhân viên hiện tại."""
        allowed = allowed_pages_for_user(
            self.db.username,
            self.employee_role,
            self.ROLE_PAGE_ACCESS,
            self.nav_buttons.keys(),
        )

        for key, button in self.nav_buttons.items():
            button.setVisible(key in allowed)

        self._refresh_sidebar_groups()

        current_key = next(
            (
                key for key, page in self.danh_sachs.items()
                if page is self.stack.currentWidget()
            ),
            None,
        )

        if current_key not in allowed:
            self.show_page("home")

from PySide6.QtCore import Qt


def show_minimizable_dialog(owner, dialog, on_finished=None):
    """
    Hiển thị QDialog dạng cửa sổ độc lập, không khóa cửa sổ chính.

    Giữ tham chiếu đến dialog trong owner để hộp thoại không bị thu gom
    trước khi người dùng đóng. Khi đóng, callback nhận mã kết quả QDialog.
    """
    flags = dialog.windowFlags()
    flags |= Qt.WindowType.Dialog
    flags |= Qt.WindowType.WindowSystemMenuHint
    flags |= Qt.WindowType.WindowMinimizeButtonHint
    flags |= Qt.WindowType.WindowCloseButtonHint
    dialog.setWindowFlags(flags)
    dialog.setWindowModality(Qt.WindowModality.NonModal)

    if not hasattr(owner, "_managed_dialogs"):
        owner._managed_dialogs = []

    owner._managed_dialogs.append(dialog)

    def _finished(result):
        if on_finished is not None:
            on_finished(result)
        try:
            owner._managed_dialogs.remove(dialog)
        except (AttributeError, ValueError):
            pass

    dialog.finished.connect(_finished)
    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog

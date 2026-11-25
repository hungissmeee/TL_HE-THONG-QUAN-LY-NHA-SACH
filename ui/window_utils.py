from PySide6.QtCore import Qt


def show_modeless_dialog(owner, dialog, on_finished=None):
    """
    Hiển thị QDialog độc lập, không khóa cửa sổ chính.

    Giữ tham chiếu đến dialog để Python không thu hồi đối tượng khi hàm gọi
    kết thúc. Khi dialog đóng, WA_DeleteOnClose sẽ giải phóng cửa sổ.
    """
    dialog.setModal(False)
    dialog.setWindowModality(Qt.WindowModality.NonModal)
    dialog.setWindowFlag(
        Qt.WindowType.WindowMinimizeButtonHint, True
    )
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

    dialogs = getattr(owner, "_modeless_dialogs", None)
    if dialogs is None:
        dialogs = []
        owner._modeless_dialogs = dialogs

    dialogs.append(dialog)
    dialog_id = id(dialog)

    def release_reference(_result=None):
        dialogs[:] = [item for item in dialogs if id(item) != dialog_id]

    dialog.finished.connect(release_reference)
    if on_finished is not None:
        dialog.finished.connect(on_finished)

    dialog.show()
    dialog.raise_()
    dialog.activateWindow()
    return dialog

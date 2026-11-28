-- Thu hồi quyền xóa/sửa chứng từ lịch sử và quyền ghi không cần thiết của nhân viên.
-- Chạy sau các migration 001-003 trên database đang sử dụng.
SET XACT_ABORT ON;
GO

-- Hóa đơn: chỉ Admin/Quản lý được hủy; không vai trò nào được xóa vật lý
-- hoặc sửa chi tiết sau khi hóa đơn đã tạo.
REVOKE UPDATE, DELETE ON OBJECT::dbo.HOA_DON FROM rl_QuanLy;
REVOKE UPDATE, DELETE ON OBJECT::dbo.CHI_TIET_HOA_DON FROM rl_QuanLy;
GRANT SELECT, INSERT ON OBJECT::dbo.CHI_TIET_HOA_DON TO rl_QuanLy;
GRANT SELECT, INSERT ON OBJECT::dbo.HOA_DON TO rl_QuanLy;
GRANT UPDATE ON OBJECT::dbo.HOA_DON (TRANGTHAI) TO rl_QuanLy;
REVOKE UPDATE ON OBJECT::dbo.HOA_DON FROM rl_ThuNgan;
REVOKE UPDATE ON OBJECT::dbo.CHI_TIET_HOA_DON FROM rl_ThuNgan;
GRANT SELECT, INSERT ON OBJECT::dbo.HOA_DON TO rl_ThuNgan;
GRANT SELECT, INSERT ON OBJECT::dbo.CHI_TIET_HOA_DON TO rl_ThuNgan;

-- Phiếu nhập: nhân viên kho chỉ được lập và sửa các cột nghiệp vụ cho phép;
-- không được tự hủy phiếu hoặc sửa người lập/ngày nhập/trạng thái.
REVOKE DELETE ON OBJECT::dbo.PHIEU_NHAP FROM rl_QuanLy;
REVOKE UPDATE ON OBJECT::dbo.PHIEU_NHAP FROM rl_QuanLy;
GRANT SELECT, INSERT ON OBJECT::dbo.PHIEU_NHAP TO rl_QuanLy;
GRANT UPDATE ON OBJECT::dbo.PHIEU_NHAP (MANCC, SHDNCC, TONGTRIGIA, TRANGTHAI) TO rl_QuanLy;
REVOKE UPDATE, DELETE ON OBJECT::dbo.PHIEU_NHAP FROM rl_NhanVienKho;
GRANT SELECT, INSERT ON OBJECT::dbo.PHIEU_NHAP TO rl_NhanVienKho;
GRANT UPDATE ON OBJECT::dbo.PHIEU_NHAP (MANCC, SHDNCC, TONGTRIGIA) TO rl_NhanVienKho;

-- Nhà cung cấp: kho chỉ cần tra cứu; quản lý dùng trạng thái hoạt động thay vì xóa cứng.
REVOKE INSERT, UPDATE, DELETE ON OBJECT::dbo.NHA_CUNG_CAP FROM rl_NhanVienKho;
GRANT SELECT ON OBJECT::dbo.NHA_CUNG_CAP TO rl_NhanVienKho;
REVOKE DELETE ON OBJECT::dbo.NHA_CUNG_CAP FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.NHA_XUAT_BAN FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.SACH FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.SAN_PHAM FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.SAN_PHAM_KHAC FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.TAC_GIA FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.THE_LOAI FROM rl_QuanLy;
REVOKE DELETE ON OBJECT::dbo.THUONG_HIEU FROM rl_QuanLy;

-- Đổi trả: Kế toán chỉ xem; Quản lý lập phiếu nhưng không sửa/xóa lịch sử.
REVOKE INSERT, UPDATE, DELETE ON OBJECT::dbo.PHIEU_DOI_TRA FROM rl_KeToan;
REVOKE INSERT, UPDATE, DELETE ON OBJECT::dbo.CHI_TIET_DOI_TRA FROM rl_KeToan;
GRANT SELECT ON OBJECT::dbo.PHIEU_DOI_TRA TO rl_KeToan;
GRANT SELECT ON OBJECT::dbo.CHI_TIET_DOI_TRA TO rl_KeToan;
REVOKE UPDATE, DELETE ON OBJECT::dbo.PHIEU_DOI_TRA FROM rl_QuanLy;
REVOKE UPDATE, DELETE ON OBJECT::dbo.CHI_TIET_DOI_TRA FROM rl_QuanLy;
GRANT SELECT, INSERT ON OBJECT::dbo.PHIEU_DOI_TRA TO rl_QuanLy;
GRANT SELECT, INSERT ON OBJECT::dbo.CHI_TIET_DOI_TRA TO rl_QuanLy;

-- Đăng ký ca: nhân viên được tự đăng ký nhưng không tự xóa lịch sử đăng ký.
REVOKE DELETE ON OBJECT::dbo.LAMCA FROM rl_ThuNgan, rl_NhanVienKho;
REVOKE INSERT, UPDATE, DELETE ON OBJECT::dbo.LAMCA FROM rl_KeToan;
GRANT SELECT, INSERT ON OBJECT::dbo.LAMCA TO rl_ThuNgan;
GRANT SELECT, INSERT ON OBJECT::dbo.LAMCA TO rl_NhanVienKho;
GRANT SELECT ON OBJECT::dbo.LAMCA TO rl_KeToan;

-- Sản phẩm: kho không được xóa mềm sản phẩm trực tiếp; thao tác ngừng dùng
-- sản phẩm được quản lý/admin kiểm soát. Tồn kho vẫn được cập nhật qua nghiệp vụ.
REVOKE UPDATE ON OBJECT::dbo.SAN_PHAM (IS_DELETED) FROM rl_NhanVienKho;

-- Kế toán chỉ đối chiếu tồn, không trực tiếp sửa số lượng kho.
REVOKE UPDATE ON OBJECT::dbo.SAN_PHAM (SLTON) FROM rl_KeToan;
GO

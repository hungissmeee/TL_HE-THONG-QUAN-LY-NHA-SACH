-- Dong bo lai quyen theo phan cong nghiep vu hien tai.
-- Chay sau migration 005 tren database da ton tai.
-- Co the chay lai an toan.
SET XACT_ABORT ON;
GO

IF DATABASE_PRINCIPAL_ID(N'rl_QuanLy') IS NULL
   OR DATABASE_PRINCIPAL_ID(N'rl_NhanVienKho') IS NULL
BEGIN
    THROW 51006, N'Thieu role Quan ly hoac Nhan vien kho.', 1;
END;
GO

-- Chi tiet phieu nhap: kho duoc them, sua va bo tung dong hang.
-- Ung dung van phai kiem tra phieu con hieu luc, khong co giao dich kho
-- phat sinh tiep theo, con it nhat mot dong va cap nhat ton/gia von trong transaction.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON OBJECT::dbo.CHI_TIET_PHIEU_NHAP TO rl_NhanVienKho;

-- Ca lam viec: khong cho Quan ly xoa rieng dang ky nhan vien.
-- Xoa ca chua bat dau se xoa cac dang ky qua FK ON DELETE CASCADE.
REVOKE DELETE ON OBJECT::dbo.LAMCA FROM rl_QuanLy;

-- Nhan vien kho khong duoc thay doi gia ban truc tiep.
-- Thu hoi ca quyen cap o muc bang, sau do cap lai cac cot can cho viec
-- cap nhat thong tin san pham va cap nhat ton/gia nhap qua nghiep vu nhap.
REVOKE UPDATE ON OBJECT::dbo.SAN_PHAM FROM rl_NhanVienKho;
GRANT UPDATE ON OBJECT::dbo.SAN_PHAM
    (BARCODE, DVT, TENSP, VAT, GIANHAP, SLTON)
    TO rl_NhanVienKho;

-- Nhan vien kho khong duoc tu y ngung su dung danh muc.
-- Van duoc sua thong tin mo ta va them moi theo phan cong hien tai.
REVOKE UPDATE ON OBJECT::dbo.NHA_XUAT_BAN FROM rl_NhanVienKho;
GRANT UPDATE ON OBJECT::dbo.NHA_XUAT_BAN (DIACHI, TENNXB)
    TO rl_NhanVienKho;

REVOKE UPDATE ON OBJECT::dbo.TAC_GIA FROM rl_NhanVienKho;
GRANT UPDATE ON OBJECT::dbo.TAC_GIA (TENTG)
    TO rl_NhanVienKho;

REVOKE UPDATE ON OBJECT::dbo.THE_LOAI FROM rl_NhanVienKho;
GRANT UPDATE ON OBJECT::dbo.THE_LOAI (TENTL)
    TO rl_NhanVienKho;

REVOKE UPDATE ON OBJECT::dbo.THUONG_HIEU FROM rl_NhanVienKho;
GRANT UPDATE ON OBJECT::dbo.THUONG_HIEU (TENTH, XUATXU)
    TO rl_NhanVienKho;
GO

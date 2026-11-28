-- Dong bo quyen SQL voi nghiep vu hien tai cua ung dung.
-- Chay sau migration 004 tren database da ton tai.
-- Co the chay lai an toan.
SET XACT_ABORT ON;
GO

IF DATABASE_PRINCIPAL_ID(N'rl_QuanLy') IS NULL
   OR DATABASE_PRINCIPAL_ID(N'rl_NhanVienKho') IS NULL
   OR DATABASE_PRINCIPAL_ID(N'rl_KeToan') IS NULL
BEGIN
    THROW 51005, N'Thieu mot trong cac database role can cap nhat quyen.', 1;
END;
GO

-- Nhap hang: kho nhap don gia tren chi tiet phieu nhap.
-- Repository dung don gia nay de tinh lai gia nhap binh quan SAN_PHAM.GIANHAP.
GRANT UPDATE ON OBJECT::dbo.SAN_PHAM (GIANHAP) TO rl_NhanVienKho;

-- Ca lam viec: quan ly chi tao va xoa ca chua bat dau, khong sua ca da tao.
REVOKE UPDATE ON OBJECT::dbo.CA_LAM_VIEC
    (NGAYLAM, SOCA, TGDONG, TGMO, TMDAUCA)
    FROM rl_QuanLy;

-- LAMCA: cac vai tro khong sua truc tiep ban ghi dang ky.
-- Quan ly van can INSERT/DELETE cho cac nghiep vu dang ky va xoa ca sap bat dau.
REVOKE INSERT, UPDATE ON OBJECT::dbo.LAMCA FROM rl_QuanLy;

-- Ke toan duoc dang ky ca dang dien ra nhu cac nhan vien khac,
-- ngoai quyen ghi TMCUOICA sau khi ca ket thuc.
GRANT SELECT, INSERT ON OBJECT::dbo.LAMCA TO rl_KeToan;

-- Nha cung cap: quan ly chi sua thong tin nghiep vu, khong cap UPDATE toan bang.
REVOKE UPDATE ON OBJECT::dbo.NHA_CUNG_CAP FROM rl_QuanLy;
GRANT UPDATE ON OBJECT::dbo.NHA_CUNG_CAP
    (DIACHI, IS_DELETED, MST, SDT, TENNCC)
    TO rl_QuanLy;

-- Bang lien ket tac gia/the loai chi duoc thay the bang DELETE + INSERT
-- khi sua san pham; ung dung khong co thao tac UPDATE truc tiep tren cac lien ket.
REVOKE UPDATE ON OBJECT::dbo.THUOC_TG FROM rl_QuanLy, rl_NhanVienKho;
REVOKE UPDATE ON OBJECT::dbo.THUOC_TL FROM rl_QuanLy, rl_NhanVienKho;
GO

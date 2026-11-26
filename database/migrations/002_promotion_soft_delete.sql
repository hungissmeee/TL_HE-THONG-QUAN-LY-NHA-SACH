-- Chay tren database hien tai neu da tao tu cac phien ban script cu.
-- Neu ung dung dang ket noi database khac CSDLTEST, thay ten database ben duoi.
USE CSDLTEST;
GO

-- Migration nay them cot (neu chua co) va chi cho rl_QuanLy cap nhat co IS_DELETED.
IF COL_LENGTH(N'dbo.CHUONG_TRINH_KM', N'IS_DELETED') IS NULL
BEGIN
    ALTER TABLE dbo.CHUONG_TRINH_KM
    ADD IS_DELETED BIT NULL;
END;
GO

-- Thu hoi quyen UPDATE/DELETE toan bang da cap truoc day.
REVOKE UPDATE, DELETE
ON dbo.CHUONG_TRINH_KM
FROM rl_QuanLy;
GO

-- Quan ly chi duoc xoa mem; khong the sua TYLEGIAM/NGAYBD/NGAYKT.
GRANT UPDATE (IS_DELETED, TENKM)
ON dbo.CHUONG_TRINH_KM
TO rl_QuanLy;
GO

-- Chay tren database hien tai neu da tao tu cac phien ban script cu.
-- Neu ung dung dang ket noi database khac CSDLTEST, thay ten database ben duoi.
USE CSDLTEST;
GO

-- Migration nay them cot (neu chua co) va chi cho rl_QuanLy cap nhat TENKM, IS_DELETED.
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

-- Thu hoi rieng quyen cap do cot da cap trong phien ban migration truoc.
REVOKE UPDATE (NGAYBD, NGAYKT)
ON dbo.CHUONG_TRINH_KM
FROM rl_QuanLy;
GO

-- Quan ly chi duoc doi ten va xoa mem; thoi gian va ty le da tao khong duoc sua.
GRANT UPDATE (IS_DELETED, TENKM)
ON dbo.CHUONG_TRINH_KM
TO rl_QuanLy;
GO

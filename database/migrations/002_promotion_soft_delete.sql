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
GRANT UPDATE (IS_DELETED)
ON dbo.CHUONG_TRINH_KM
TO rl_QuanLy;
GO

-- Chan thay doi ty le giam va thoi han, ke ca khi cap nhat truc tiep bang SQL.
CREATE OR ALTER TRIGGER dbo.TR_CHUONG_TRINH_KM_BAT_BIEN
ON dbo.CHUONG_TRINH_KM
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM inserted AS I
        INNER JOIN deleted AS D ON D.MAKM = I.MAKM
        WHERE EXISTS (
            SELECT I.TYLEGIAM, I.NGAYBD, I.NGAYKT
            EXCEPT
            SELECT D.TYLEGIAM, D.NGAYBD, D.NGAYKT
        )
    )
    BEGIN
        THROW 50001, N'Khong duoc thay doi ty le giam hoac thoi han cua chuong trinh khuyen mai da tao.', 1;
    END;
END;
GO

-- Them cot BARCODE vao bang SAN_PHAM cho database da tao truoc day.
-- Neu dung database khac CSDLTEST, thay ten database ben duoi.
USE CSDLTEST;
GO

IF COL_LENGTH(N'dbo.SAN_PHAM', N'BARCODE') IS NULL
BEGIN
    ALTER TABLE dbo.SAN_PHAM
    ADD BARCODE VARCHAR(50) NULL;
END;
GO

GRANT UPDATE (BARCODE)
ON dbo.SAN_PHAM
TO rl_QuanLy;
GO

GRANT UPDATE (BARCODE)
ON dbo.SAN_PHAM
TO rl_NhanVienKho;
GO

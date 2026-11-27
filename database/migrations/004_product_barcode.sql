-- Them cot BARCODE vao bang SAN_PHAM cho database hien tai.
-- Chay file nay sau database/script.sql.
-- Neu dung database khac CSDLTEST, thay ten database ben duoi.
USE CSDLTEST;
GO

IF COL_LENGTH(N'dbo.SAN_PHAM', N'BARCODE') IS NULL
BEGIN
    ALTER TABLE dbo.SAN_PHAM
    ADD BARCODE VARCHAR(50) NULL;
END;
GO

-- Ma vach khong duoc trung; cho phep de NULL hoac chuoi rong.
IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.SAN_PHAM')
      AND name = N'UX_SAN_PHAM_BARCODE'
)
BEGIN
    CREATE UNIQUE INDEX UX_SAN_PHAM_BARCODE
    ON dbo.SAN_PHAM (BARCODE)
    WHERE BARCODE IS NOT NULL AND BARCODE <> '';
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

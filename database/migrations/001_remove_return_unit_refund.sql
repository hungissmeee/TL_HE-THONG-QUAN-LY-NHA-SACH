-- Chay mot lan tren database da ton tai truoc khi cap nhat phan mem.
-- Schema moi trong database/script.sql da bo cot DONGIAHOAN.
-- Migration giu nguyen tong tien hoan o PHIEU_DOI_TRA.TONG_TIEN_HOAN.

IF COL_LENGTH(N'dbo.CHI_TIET_DOI_TRA', N'DONGIAHOAN') IS NOT NULL
BEGIN
    IF OBJECT_ID(N'dbo.CK_CTDT_DONGIAHOAN_KHONG_AM', N'C') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_DOI_TRA
        DROP CONSTRAINT CK_CTDT_DONGIAHOAN_KHONG_AM;
    END;

    ALTER TABLE dbo.CHI_TIET_DOI_TRA
    DROP COLUMN DONGIAHOAN;
END;
GO

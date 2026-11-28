-- Them GIAVON vao chi tiet hoa don de co dinh gia von tai thoi diem ban.
-- Chay mot lan (co the chay lai an toan) tren database da ton tai.
--
-- Du lieu hoa don cu chua tung luu gia von tai thoi diem ban. Migration uoc tinh
-- bang gia nhap binh quan gia quyen tu cac phieu nhap con hieu luc den thoi diem
-- lap hoa don. Neu khong co lich su nhap phu hop, dung GIANHAP hien tai lam gia tri
-- thay the tot nhat co the. Cac hoa don tao sau migration se luu chinh xac GIAVON.

IF COL_LENGTH(N'dbo.CHI_TIET_HOA_DON', N'GIAVON') IS NULL
BEGIN
    ALTER TABLE dbo.CHI_TIET_HOA_DON
    ADD GIAVON DECIMAL(15, 2) NULL;
END;
GO

UPDATE CT
SET GIAVON = CAST(
    COALESCE(HISTORY.AVG_COST, SP.GIANHAP, 0)
    AS DECIMAL(15, 2)
)
FROM dbo.CHI_TIET_HOA_DON CT
INNER JOIN dbo.HOA_DON HD ON HD.MAHD = CT.MAHD
INNER JOIN dbo.SAN_PHAM SP ON SP.MASP = CT.MASP
OUTER APPLY (
    SELECT
        SUM(CTPN.DONGIA * CTPN.SOLUONG)
            / NULLIF(SUM(CTPN.SOLUONG), 0) AS AVG_COST
    FROM dbo.CHI_TIET_PHIEU_NHAP CTPN
    INNER JOIN dbo.PHIEU_NHAP PN ON PN.MAPN = CTPN.MAPN
    WHERE CTPN.MASP = CT.MASP
      AND ISNULL(PN.TRANGTHAI, 1) = 1
      AND PN.NGAYNHAP <= HD.NGAYLAP
) HISTORY
WHERE CT.GIAVON IS NULL;
GO

IF EXISTS (
    SELECT 1
    FROM dbo.CHI_TIET_HOA_DON
    WHERE GIAVON IS NULL
)
BEGIN
    THROW 51030, N'Khong the backfill GIAVON cho mot so chi tiet hoa don.', 1;
END;
GO

ALTER TABLE dbo.CHI_TIET_HOA_DON
ALTER COLUMN GIAVON DECIMAL(15, 2) NOT NULL;
GO

IF OBJECT_ID(N'dbo.CK_CTHD_GIAVON_KHONG_AM', N'C') IS NULL
BEGIN
    ALTER TABLE dbo.CHI_TIET_HOA_DON
    ADD CONSTRAINT CK_CTHD_GIAVON_KHONG_AM CHECK (GIAVON >= 0);
END;
GO

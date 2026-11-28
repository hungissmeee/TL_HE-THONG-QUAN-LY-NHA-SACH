-- Cap quyen doc lich su doi tra cho nhan vien kho.
-- Chay script nay mot lan tren database CSDLQLNHASACH hien tai.
-- Khong thay doi du lieu, bang hoac cau truc schema.

IF DATABASE_PRINCIPAL_ID(N'rl_NhanVienKho') IS NULL
BEGIN
    THROW 51001, N'Khong tim thay database role rl_NhanVienKho. Hay tao role truoc khi cap quyen.', 1;
END;
GO

GRANT SELECT ON OBJECT::dbo.PHIEU_DOI_TRA TO rl_NhanVienKho;
GRANT SELECT ON OBJECT::dbo.CHI_TIET_DOI_TRA TO rl_NhanVienKho;
GO

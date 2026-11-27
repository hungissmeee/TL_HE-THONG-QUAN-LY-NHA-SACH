/*
    Cap quyen toi thieu cho tai khoan dich vu Web quan ly san pham.
    Chay tren database CSDLTEST sau khi da tao SQL Login bookhub_web_app.
    Khong cap db_owner, db_datareader hoac db_datawriter.
*/
USE CSDLTEST;
GO

IF SUSER_ID(N'bookhub_web_app') IS NULL
    THROW 51000, N'Chua ton tai SQL Login bookhub_web_app. Hay tao login va user theo huong dan Web truoc.', 1;
GO

IF DATABASE_PRINCIPAL_ID(N'rl_BookHubWeb') IS NULL
    EXEC(N'CREATE ROLE rl_BookHubWeb AUTHORIZATION dbo;');
GO

IF DATABASE_PRINCIPAL_ID(N'bookhub_web_app') IS NULL
    CREATE USER bookhub_web_app FOR LOGIN bookhub_web_app;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.database_role_members AS drm
    JOIN sys.database_principals AS role_principal
      ON role_principal.principal_id = drm.role_principal_id
    JOIN sys.database_principals AS member_principal
      ON member_principal.principal_id = drm.member_principal_id
    WHERE role_principal.name = N'rl_BookHubWeb'
      AND member_principal.name = N'bookhub_web_app'
)
    ALTER ROLE rl_BookHubWeb ADD MEMBER bookhub_web_app;
GO

-- Quyen doc phuc vu danh sach, chi tiet, tim kiem ISBN va du lieu form.
GRANT SELECT ON dbo.SAN_PHAM TO rl_BookHubWeb;
GRANT SELECT ON dbo.SACH TO rl_BookHubWeb;
GRANT SELECT ON dbo.SAN_PHAM_KHAC TO rl_BookHubWeb;
GRANT SELECT ON dbo.NHA_XUAT_BAN TO rl_BookHubWeb;
GRANT SELECT ON dbo.TAC_GIA TO rl_BookHubWeb;
GRANT SELECT ON dbo.THE_LOAI TO rl_BookHubWeb;
GRANT SELECT ON dbo.THUONG_HIEU TO rl_BookHubWeb;
GRANT SELECT ON dbo.THUOC_TG TO rl_BookHubWeb;
GRANT SELECT ON dbo.THUOC_TL TO rl_BookHubWeb;
GO

-- Them san pham; gia nhap va ton kho van do quy trinh nhap/xuat hang quan ly.
GRANT INSERT ON dbo.SAN_PHAM TO rl_BookHubWeb;
GRANT INSERT ON dbo.SACH TO rl_BookHubWeb;
GRANT INSERT ON dbo.SAN_PHAM_KHAC TO rl_BookHubWeb;
GRANT INSERT ON dbo.THUOC_TG TO rl_BookHubWeb;
GRANT INSERT ON dbo.THUOC_TL TO rl_BookHubWeb;
GO

-- Chi cho sua cac cot duoc phep tu form san pham.
GRANT UPDATE ON dbo.SAN_PHAM (TENSP, BARCODE, DVT, GIABAN, VAT) TO rl_BookHubWeb;
GRANT UPDATE ON dbo.SACH (ISBN, NAMXB, MANXB) TO rl_BookHubWeb;
GRANT UPDATE ON dbo.SAN_PHAM_KHAC (NGAYSX, MATH) TO rl_BookHubWeb;
GRANT DELETE ON dbo.THUOC_TG TO rl_BookHubWeb;
GRANT DELETE ON dbo.THUOC_TL TO rl_BookHubWeb;
GRANT UPDATE ON dbo.SAN_PHAM (IS_DELETED) TO rl_BookHubWeb;
GO

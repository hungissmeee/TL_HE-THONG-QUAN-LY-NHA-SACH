/*
    Mo rong quyen SQL toi thieu cho cac phan he Web:
    nha cung cap, danh muc, khuyen mai, hoa don, phieu nhap,
    doi tra, nhan su co ban, ca lam viec va bao cao.
    Chay sau 005_bookhub_web_products_permissions.sql.
    Khong cap quyen quan tri SQL Server hay db_owner.
*/
USE CSDLTEST;
GO

IF DATABASE_PRINCIPAL_ID(N'rl_BookHubWeb') IS NULL
    THROW 51010, N'Chua co role rl_BookHubWeb. Hay chay migration 005 truoc.', 1;
GO

-- QUYEN DOC: danh sach, chi tiet, tra cuu, thong ke va bao cao.
GRANT SELECT ON dbo.NHA_CUNG_CAP TO rl_BookHubWeb;
GRANT SELECT ON dbo.NHA_XUAT_BAN TO rl_BookHubWeb;
GRANT SELECT ON dbo.TAC_GIA TO rl_BookHubWeb;
GRANT SELECT ON dbo.THE_LOAI TO rl_BookHubWeb;
GRANT SELECT ON dbo.THUONG_HIEU TO rl_BookHubWeb;
GRANT SELECT ON dbo.CHUONG_TRINH_KM TO rl_BookHubWeb;
GRANT SELECT ON dbo.NHAN_VIEN TO rl_BookHubWeb;
GRANT SELECT ON dbo.CA_LAM_VIEC TO rl_BookHubWeb;
GRANT SELECT ON dbo.LAMCA TO rl_BookHubWeb;
GRANT SELECT ON dbo.PHIEU_NHAP TO rl_BookHubWeb;
GRANT SELECT ON dbo.CHI_TIET_PHIEU_NHAP TO rl_BookHubWeb;
GRANT SELECT ON dbo.HOA_DON TO rl_BookHubWeb;
GRANT SELECT ON dbo.CHI_TIET_HOA_DON TO rl_BookHubWeb;
GRANT SELECT ON dbo.PHIEU_DOI_TRA TO rl_BookHubWeb;
GRANT SELECT ON dbo.CHI_TIET_DOI_TRA TO rl_BookHubWeb;
GO

-- NHA CUNG CAP: them, sua ho so va ngung/kich hoat mem.
GRANT INSERT ON dbo.NHA_CUNG_CAP TO rl_BookHubWeb;
GRANT UPDATE ON dbo.NHA_CUNG_CAP (TENNCC, SDT, DIACHI, MST, IS_DELETED) TO rl_BookHubWeb;
GO

-- DANH MUC: tao, sua va xoa mem; khong xoa vat ly.
GRANT INSERT ON dbo.TAC_GIA TO rl_BookHubWeb;
GRANT UPDATE ON dbo.TAC_GIA (TENTG, IS_DELETED) TO rl_BookHubWeb;

GRANT INSERT ON dbo.THE_LOAI TO rl_BookHubWeb;
GRANT UPDATE ON dbo.THE_LOAI (TENTL, IS_DELETED) TO rl_BookHubWeb;

GRANT INSERT ON dbo.NHA_XUAT_BAN TO rl_BookHubWeb;
GRANT UPDATE ON dbo.NHA_XUAT_BAN (TENNXB, DIACHI, IS_DELETED) TO rl_BookHubWeb;

GRANT INSERT ON dbo.THUONG_HIEU TO rl_BookHubWeb;
GRANT UPDATE ON dbo.THUONG_HIEU (TENTH, XUATXU, IS_DELETED) TO rl_BookHubWeb;
GO

-- KHUYEN MAI: tao, doi ten va ngung ap dung.
GRANT INSERT ON dbo.CHUONG_TRINH_KM TO rl_BookHubWeb;
GRANT UPDATE ON dbo.CHUONG_TRINH_KM (TENKM, IS_DELETED) TO rl_BookHubWeb;
GO

-- NHAP KHO: tao chung tu/chi tiet, cap nhat ton va gia nhap binh quan.
GRANT INSERT ON dbo.PHIEU_NHAP TO rl_BookHubWeb;
GRANT INSERT ON dbo.CHI_TIET_PHIEU_NHAP TO rl_BookHubWeb;
GRANT UPDATE ON dbo.PHIEU_NHAP (TRANGTHAI) TO rl_BookHubWeb;
GRANT UPDATE ON dbo.SAN_PHAM (GIANHAP, SLTON) TO rl_BookHubWeb;
GO

-- HOA DON: tao chung tu/chi tiet, tru ton; huy bang cap nhat trang thai va hoan kho.
GRANT INSERT ON dbo.HOA_DON TO rl_BookHubWeb;
GRANT INSERT ON dbo.CHI_TIET_HOA_DON TO rl_BookHubWeb;
GRANT UPDATE ON dbo.HOA_DON (TRANGTHAI) TO rl_BookHubWeb;
GRANT UPDATE ON dbo.SAN_PHAM (SLTON) TO rl_BookHubWeb;
GO

-- DOI TRA: tao/xoa chung tu va chi tiet, bien dong ton kho theo quy tac nghiep vu.
GRANT INSERT ON dbo.PHIEU_DOI_TRA TO rl_BookHubWeb;
GRANT INSERT ON dbo.CHI_TIET_DOI_TRA TO rl_BookHubWeb;
GRANT DELETE ON dbo.PHIEU_DOI_TRA TO rl_BookHubWeb;
GRANT DELETE ON dbo.CHI_TIET_DOI_TRA TO rl_BookHubWeb;
GO

-- CA LAM VIEC: tao/xoa ca, dang ky nhan vien va chot tien cuoi ca.
GRANT INSERT ON dbo.CA_LAM_VIEC TO rl_BookHubWeb;
GRANT DELETE ON dbo.CA_LAM_VIEC TO rl_BookHubWeb;
GRANT UPDATE ON dbo.CA_LAM_VIEC (TMCUOICA) TO rl_BookHubWeb;
GRANT INSERT ON dbo.LAMCA TO rl_BookHubWeb;
GRANT DELETE ON dbo.LAMCA TO rl_BookHubWeb;
GO

-- NHAN VIEN: Web chi cap nhat ho so; khong co quyen quan ly SQL Login/Database User.
GRANT UPDATE ON dbo.NHAN_VIEN (TENNV, SDT) TO rl_BookHubWeb;
GO

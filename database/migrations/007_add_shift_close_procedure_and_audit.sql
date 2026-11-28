-- Don dep neu migration 007 phien ban cu da tao nhat ky va thu tuc chot ca.
-- Nghiep vu chot ca hien duoc kiem tra trong Python; khong can bang log/trigger/procedure.
SET XACT_ABORT ON;
GO

DROP TRIGGER IF EXISTS dbo.trg_Audit_PHIEU_NHAP;
DROP TRIGGER IF EXISTS dbo.trg_Audit_CHI_TIET_PHIEU_NHAP;
DROP TRIGGER IF EXISTS dbo.trg_Audit_HOA_DON;
DROP TRIGGER IF EXISTS dbo.trg_Audit_CHI_TIET_HOA_DON;
DROP TRIGGER IF EXISTS dbo.trg_Audit_SAN_PHAM;
DROP TRIGGER IF EXISTS dbo.trg_Audit_CA_LAM_VIEC;
DROP TRIGGER IF EXISTS dbo.trg_Audit_LAMCA;
DROP TRIGGER IF EXISTS dbo.trg_Audit_PHIEU_DOI_TRA;
DROP TRIGGER IF EXISTS dbo.trg_Audit_CHI_TIET_DOI_TRA;
DROP PROCEDURE IF EXISTS dbo.usp_GhiTienCuoiCa;
DROP TABLE IF EXISTS dbo.NHAT_KY_THAY_DOI;
GO

-- Kich hoat lai quyen chot ca truc tiep cho Ke toan.
REVOKE UPDATE ON OBJECT::dbo.CA_LAM_VIEC FROM rl_KeToan;
GRANT UPDATE ON OBJECT::dbo.CA_LAM_VIEC (TMCUOICA) TO rl_KeToan;
GO

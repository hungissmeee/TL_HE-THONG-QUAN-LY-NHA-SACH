-- Thu ngan can doc ma hoa don trong PHIEU_DOI_TRA de kiem tra
-- hoa don da phat sinh doi tra truoc khi thuc hien huy hoa don.
USE CSDLTEST;
GO

GRANT SELECT ON dbo.PHIEU_DOI_TRA (MAHD)
TO rl_ThuNgan;
GO

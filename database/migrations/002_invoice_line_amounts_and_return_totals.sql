/*
    Migration 002: Luu thanh tien theo dong hoa don va tong tien hoan theo dong.

    Chay tren database da ton tai sau khi sao luu du lieu.
    Khong sua lai TONG_TIEN_HOAN cua phieu cu: migration giu nguyen tong tien
    da ghi nhan, chi chuyen DONGIAHOAN * SOLUONG sang TONGTIENHOAN.
*/

SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    DECLARE @NeedInvoiceLineBackfill BIT = 0;

    IF COL_LENGTH(N'dbo.CHI_TIET_HOA_DON', N'THANHTIEN') IS NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_HOA_DON
        ADD THANHTIEN DECIMAL(15, 2) NULL;

        SET @NeedInvoiceLineBackfill = 1;
    END;

    IF COL_LENGTH(N'dbo.CHI_TIET_HOA_DON', N'THANHTIENSAUGIAM') IS NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_HOA_DON
        ADD THANHTIENSAUGIAM DECIMAL(15, 2) NULL;

        SET @NeedInvoiceLineBackfill = 1;
    END;

    /*
       Backfill hóa đơn cũ:
       - Thành tiền = đơn giá * số lượng.
       - Tính giảm giá trên toàn hóa đơn.
       - Phân bổ giảm giá theo tỷ trọng từng dòng.
       - Phần dư làm tròn được phân bổ theo phần lẻ lớn nhất;
         MASP được dùng làm tiêu chí phụ để kết quả ổn định.
    */
    IF @NeedInvoiceLineBackfill = 1
    BEGIN
        ;WITH LineAmounts AS (
            SELECT
                CT.MAHD,
                CT.MASP,
                CAST(ROUND(
                    COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0),
                    2
                ) AS DECIMAL(15, 2)) AS THANHTIEN,
                CAST(SUM(
                    COALESCE(CT.DONGIA, 0) * COALESCE(CT.SOLUONG, 0)
                ) OVER (PARTITION BY CT.MAHD) AS DECIMAL(28, 2)) AS TONGTIEN,
                CAST(COALESCE(KM.TYLEGIAM, 0) AS DECIMAL(5, 2)) AS TYLEGIAM
            FROM dbo.CHI_TIET_HOA_DON CT
            INNER JOIN dbo.HOA_DON HD ON HD.MAHD = CT.MAHD
            LEFT JOIN dbo.CHUONG_TRINH_KM KM ON KM.MAKM = HD.MAKM
        ),
        InvoiceDiscounts AS (
            SELECT
                MAHD,
                MASP,
                THANHTIEN,
                TONGTIEN,
                CAST(ROUND(TONGTIEN * TYLEGIAM / 100.0, 2) AS DECIMAL(15, 2))
                    AS TONGGIAM
            FROM LineAmounts
        ),
        RawShares AS (
            SELECT
                MAHD,
                MASP,
                THANHTIEN,
                TONGGIAM,
                CAST(
                    CASE WHEN TONGTIEN > 0
                        THEN TONGGIAM
                             * (CAST(THANHTIEN AS DECIMAL(28, 10))
                                / CAST(TONGTIEN AS DECIMAL(28, 10)))
                        ELSE 0
                    END AS DECIMAL(28, 8)
                ) AS GIAM_CHUA_LAM_TRON
            FROM InvoiceDiscounts
        ),
        RoundedShares AS (
            SELECT
                MAHD,
                MASP,
                THANHTIEN,
                TONGGIAM,
                CAST(FLOOR(GIAM_CHUA_LAM_TRON * 100) / 100.0 AS DECIMAL(15, 2))
                    AS GIAM_CO_SO,
                GIAM_CHUA_LAM_TRON
            FROM RawShares
        ),
        RankedShares AS (
            SELECT
                MAHD,
                MASP,
                THANHTIEN,
                TONGGIAM,
                GIAM_CO_SO,
                SUM(GIAM_CO_SO) OVER (PARTITION BY MAHD) AS TONG_GIAM_CO_SO,
                ROW_NUMBER() OVER (
                    PARTITION BY MAHD
                    ORDER BY
                        (GIAM_CHUA_LAM_TRON - GIAM_CO_SO) DESC,
                        MASP ASC
                ) AS THU_TU_PHAN_BO
            FROM RoundedShares
        ),
        FinalAmounts AS (
            SELECT
                MAHD,
                MASP,
                THANHTIEN,
                GIAM_CO_SO,
                CAST(ROUND(
                    (TONGGIAM - TONG_GIAM_CO_SO) * 100,
                    0
                ) AS INT) AS SO_XU_CON_LAI,
                THU_TU_PHAN_BO
            FROM RankedShares
        )
        UPDATE CT
        SET
            CT.THANHTIEN = F.THANHTIEN,
            CT.THANHTIENSAUGIAM = CAST(
                F.THANHTIEN
                - F.GIAM_CO_SO
                - CASE WHEN F.THU_TU_PHAN_BO <= F.SO_XU_CON_LAI
                    THEN 0.01 ELSE 0.00 END
                AS DECIMAL(15, 2)
            )
        FROM dbo.CHI_TIET_HOA_DON CT
        INNER JOIN FinalAmounts F
            ON F.MAHD = CT.MAHD AND F.MASP = CT.MASP;
    END;

    IF OBJECT_ID(N'dbo.CK_CTHD_THANHTIEN_KHONG_AM', N'C') IS NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_HOA_DON
        ADD CONSTRAINT CK_CTHD_THANHTIEN_KHONG_AM
            CHECK (THANHTIEN >= 0);
    END;

    IF OBJECT_ID(N'dbo.CK_CTHD_THANHTIENSAUGIAM_HOP_LE', N'C') IS NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_HOA_DON
        ADD CONSTRAINT CK_CTHD_THANHTIENSAUGIAM_HOP_LE
            CHECK (THANHTIENSAUGIAM >= 0
                   AND THANHTIENSAUGIAM <= THANHTIEN);
    END;

    /*
       Đổi tên cột cũ và chuyển giá trị lịch sử từ đơn giá hoàn
       sang tổng tiền hoàn của cả dòng.
       Điều kiện tên cột cũ giúp migration có thể chạy lại mà không nhân
       SOLUONG thêm lần nữa.
    */
    IF COL_LENGTH(N'dbo.CHI_TIET_DOI_TRA', N'DONGIAHOAN') IS NOT NULL
       AND COL_LENGTH(N'dbo.CHI_TIET_DOI_TRA', N'TONGTIENHOAN') IS NULL
    BEGIN
        EXEC sys.sp_rename
            N'dbo.CHI_TIET_DOI_TRA.DONGIAHOAN',
            N'TONGTIENHOAN',
            N'COLUMN';

        UPDATE dbo.CHI_TIET_DOI_TRA
        SET TONGTIENHOAN = CAST(
            ROUND(
                COALESCE(TONGTIENHOAN, 0) * COALESCE(SOLUONG, 0),
                2
            ) AS DECIMAL(15, 2)
        );
    END
    ELSE IF COL_LENGTH(N'dbo.CHI_TIET_DOI_TRA', N'TONGTIENHOAN') IS NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_DOI_TRA
        ADD TONGTIENHOAN DECIMAL(15, 2) NULL;
    END;

    IF OBJECT_ID(N'dbo.CK_CTDT_DONGIAHOAN_KHONG_AM', N'C') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_DOI_TRA
        DROP CONSTRAINT CK_CTDT_DONGIAHOAN_KHONG_AM;
    END;

    IF OBJECT_ID(N'dbo.CK_CTDT_TONGTIENHOAN_KHONG_AM', N'C') IS NULL
    BEGIN
        ALTER TABLE dbo.CHI_TIET_DOI_TRA
        ADD CONSTRAINT CK_CTDT_TONGTIENHOAN_KHONG_AM
            CHECK (TONGTIENHOAN >= 0);
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0
        ROLLBACK TRANSACTION;

    THROW;
END CATCH;

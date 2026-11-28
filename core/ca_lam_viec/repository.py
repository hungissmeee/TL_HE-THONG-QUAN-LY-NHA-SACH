"""Repository SQL và transaction cho ca làm việc."""

from core.sql_support import resolve_connection


class CaLamViecRepository:
    """Đọc lịch ca và thực hiện đăng ký, tạo, chốt tiền, xóa ca."""

    def __init__(self, connection_source):
        self.connection_source = connection_source

    def _connection(self):
        return resolve_connection(self.connection_source)

    def get_employee_role(self, username):
        if str(username or "").strip().casefold() == "admin":
            return "Quản trị hệ thống"
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT VAITRO FROM dbo.NHAN_VIEN WHERE MANV = ?",
                str(username or "").strip(),
            )
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Không tìm thấy hồ sơ nhân viên đang đăng nhập.")
            return str(row[0] or "").strip()
        finally:
            cursor.close()

    def get_server_time(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT SYSDATETIME()")
            return cursor.fetchone()[0]
        finally:
            cursor.close()

    def list_employee_shifts(self, username, is_accountant=False):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    C.MACA,
                    C.SOCA,
                    CAST(C.NGAYLAM AS DATE) AS NGAYLAM,
                    C.TGMO,
                    C.TGDONG,
                    COUNT(DISTINCT L.MANV) AS EmployeeCount,
                    CASE
                        WHEN MAX(CASE WHEN L.MANV = ? THEN 1 ELSE 0 END) = 1
                        THEN 1 ELSE 0
                    END AS IsRegistered,
                    C.TMCUOICA,
                    CASE WHEN SYSDATETIME() >= T.EndAt THEN 1 ELSE 0 END AS IsEnded
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY,
                                CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE C.TGMO IS NOT NULL
                  AND C.TGDONG IS NOT NULL
                  AND (
                        (SYSDATETIME() >= T.StartAt AND SYSDATETIME() < T.EndAt)
                        OR
                        (? = 1 AND SYSDATETIME() >= T.EndAt AND C.TMCUOICA IS NULL)
                  )
                GROUP BY C.MACA, C.SOCA, C.NGAYLAM, C.TGMO, C.TGDONG,
                         C.TMCUOICA, T.EndAt
                ORDER BY C.NGAYLAM DESC, C.SOCA;
            """, str(username or ""), int(bool(is_accountant)))
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def register_current_shift(self, shift_id, username):
        """Kiểm tra thời gian, tài khoản gốc, trùng ca và ghi đăng ký nguyên tử."""
        conn = self._connection()
        cursor = conn.cursor()
        sql = """
            SET XACT_ABORT ON;
            DECLARE @Maca INT = ?;
            DECLARE @Manv VARCHAR(20) = ?;
            DECLARE @Now DATETIME2 = SYSDATETIME();
            DECLARE @WorkDate DATE;
            DECLARE @StartTime TIME;
            DECLARE @EndTime TIME;
            DECLARE @StartAt DATETIME2;
            DECLARE @EndAt DATETIME2;
            DECLARE @ClosingCash DECIMAL(15,2);

            IF LOWER(ORIGINAL_LOGIN()) <> LOWER(@Manv)
                THROW 51100, N'Tài khoản SQL Server không khớp với mã nhân viên.', 1;

            SELECT
                @WorkDate = CAST(NGAYLAM AS DATE),
                @StartTime = TGMO,
                @EndTime = TGDONG,
                @ClosingCash = TMCUOICA
            FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
            WHERE MACA = @Maca;

            IF @WorkDate IS NULL OR @StartTime IS NULL OR @EndTime IS NULL
                THROW 51101, N'Không tìm thấy ca hoặc ca chưa được cấu hình giờ làm.', 1;

            SET @StartAt = DATEADD(
                SECOND,
                DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @StartTime),
                CAST(@WorkDate AS DATETIME2)
            );

            SET @EndAt = DATEADD(
                SECOND,
                DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @EndTime),
                DATEADD(
                    DAY,
                    CASE WHEN @EndTime <= @StartTime THEN 1 ELSE 0 END,
                    CAST(@WorkDate AS DATETIME2)
                )
            );

            IF NOT (@Now >= @StartAt AND @Now < @EndAt)
                THROW 51102, N'Chỉ được đăng ký ca đang diễn ra tại thời điểm hiện tại.', 1;

            IF @ClosingCash IS NOT NULL
                THROW 51103, N'Ca này đã được chốt, không thể đăng ký thêm.', 1;

            IF EXISTS (
                SELECT 1 FROM dbo.LAMCA
                WHERE MANV = @Manv AND MACA = @Maca
            )
                THROW 51104, N'Bạn đã đăng ký ca này rồi.', 1;

            IF EXISTS (
                SELECT 1
                FROM dbo.LAMCA L
                INNER JOIN dbo.CA_LAM_VIEC C ON C.MACA = L.MACA
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS ExistingStartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY,
                                CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS ExistingEndAt
                ) ExistingShift
                WHERE L.MANV = @Manv
                  AND C.MACA <> @Maca
                  AND C.TGMO IS NOT NULL
                  AND C.TGDONG IS NOT NULL
                  AND @StartAt < ExistingShift.ExistingEndAt
                  AND @EndAt > ExistingShift.ExistingStartAt
            )
                THROW 51105, N'Ca này bị trùng thời gian với ca bạn đã đăng ký.', 1;

            INSERT INTO dbo.LAMCA (MANV, MACA)
            VALUES (@Manv, @Maca);
        """
        try:
            cursor.execute(sql, int(shift_id), str(username or "").strip())
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def record_closing_cash(self, shift_id, username, closing_cash):
        """Kế toán ghi tiền cuối ca sau thời điểm kết thúc, chỉ một lần."""
        conn = self._connection()
        cursor = conn.cursor()
        sql = """
            SET XACT_ABORT ON;
            DECLARE @Maca INT = ?;
            DECLARE @Manv VARCHAR(20) = ?;
            DECLARE @Cash DECIMAL(15,2) = ?;
            DECLARE @Now DATETIME2 = SYSDATETIME();
            DECLARE @WorkDate DATE;
            DECLARE @StartTime TIME;
            DECLARE @EndTime TIME;
            DECLARE @EndAt DATETIME2;
            DECLARE @ExistingCash DECIMAL(15,2);

            IF LOWER(@Manv) <> N'admin'
               AND LOWER(ORIGINAL_LOGIN()) <> LOWER(@Manv)
                THROW 51200, N'Tài khoản SQL Server không khớp với nhân viên kế toán.', 1;

            IF LOWER(@Manv) <> N'admin'
               AND NOT EXISTS (
                    SELECT 1
                    FROM dbo.NHAN_VIEN
                    WHERE MANV = @Manv
                      AND LTRIM(RTRIM(VAITRO)) = N'Kế toán'
               )
                THROW 51201, N'Chỉ nhân viên có vai trò Kế toán được ghi tiền cuối ca.', 1;

            SELECT
                @WorkDate = CAST(NGAYLAM AS DATE),
                @StartTime = TGMO,
                @EndTime = TGDONG,
                @ExistingCash = TMCUOICA
            FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
            WHERE MACA = @Maca;

            IF @WorkDate IS NULL OR @EndTime IS NULL OR @StartTime IS NULL
                THROW 51202, N'Không tìm thấy ca hoặc ca chưa có giờ làm hợp lệ.', 1;

            SET @EndAt = DATEADD(
                SECOND,
                DATEDIFF(SECOND, CAST('00:00:00' AS TIME), @EndTime),
                DATEADD(
                    DAY,
                    CASE WHEN @EndTime <= @StartTime THEN 1 ELSE 0 END,
                    CAST(@WorkDate AS DATETIME2)
                )
            );

            IF @Now < @EndAt
                THROW 51203, N'Chỉ được ghi tiền sau khi ca đã kết thúc.', 1;

            IF @ExistingCash IS NOT NULL
                THROW 51204, N'Tiền cuối ca đã được ghi trước đó. Mỗi ca chỉ được ghi một lần.', 1;

            UPDATE dbo.CA_LAM_VIEC
            SET TMCUOICA = @Cash
            WHERE MACA = @Maca AND TMCUOICA IS NULL;

            IF @@ROWCOUNT <> 1
                THROW 51205, N'Không thể ghi tiền. Có thể ca đã được chốt bởi kế toán khác.', 1;
        """
        try:
            cursor.execute(
                sql, int(shift_id), str(username or "").strip(), closing_cash
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def create_shift(self, values):
        """Tạo một trong ba ca cố định; UNIQUE(NGAYLAM, SOCA) chặn race condition."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
                WHERE CONVERT(date, NGAYLAM) = ? AND SOCA = ?
            """, values["ngaylam"], values["soca"])
            if int(cursor.fetchone()[0] or 0) > 0:
                raise ValueError(
                    f"Ca {values['soca']} đã tồn tại trong ngày {values['ngaylam']}."
                )
            cursor.execute("""
                INSERT INTO dbo.CA_LAM_VIEC
                    (SOCA, TGMO, TGDONG, NGAYLAM, TMDAUCA, TMCUOICA)
                OUTPUT INSERTED.MACA
                VALUES (?, ?, ?, ?, ?, NULL)
            """, values["soca"], values["tgmo"], values["tgdong"],
                 values["ngaylam"], values["tmdauca"])
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("SQL Server không trả về mã ca vừa tạo.")
            shift_id = int(row[0])
            conn.commit()
            return shift_id
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def get_manager_summary(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT SYSDATETIME()")
            server_now = cursor.fetchone()[0]
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT C.MACA),
                    COUNT(DISTINCT L.MANV)
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE SYSDATETIME() >= T.StartAt AND SYSDATETIME() < T.EndAt
            """)
            active = cursor.fetchone()
            cursor.execute("""
                SELECT COUNT(*)
                FROM dbo.CA_LAM_VIEC
                WHERE NGAYLAM >= CONVERT(date, SYSDATETIME())
                  AND NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
            """)
            today_count = int(cursor.fetchone()[0] or 0)
            return {
                "server_time": server_now,
                "active_shifts": int(active[0] or 0),
                "active_employees": int(active[1] or 0),
                "today_shifts": today_count,
            }
        finally:
            cursor.close()

    def list_current_shifts(self):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG,
                    COUNT(DISTINCT L.MANV), C.TMCUOICA
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE SYSDATETIME() >= T.StartAt AND SYSDATETIME() < T.EndAt
                GROUP BY C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG, C.TMCUOICA
                ORDER BY C.SOCA
            """)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_shift_history(self, period="all"):
        if period not in {"all", "today", "7days", "30days"}:
            raise ValueError("Khoảng thời gian lịch sử ca không hợp lệ.")
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DECLARE @Period VARCHAR(10) = ?;
                SELECT
                    C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG,
                    COUNT(DISTINCT L.MANV), C.TMDAUCA, C.TMCUOICA,
                    CASE
                        WHEN SYSDATETIME() >= T.StartAt AND SYSDATETIME() < T.EndAt
                            THEN N'Đang diễn ra'
                        WHEN SYSDATETIME() < T.StartAt
                            THEN N'Sắp bắt đầu'
                        ELSE N'Đã kết thúc'
                    END AS ShiftStatus
                FROM dbo.CA_LAM_VIEC C
                CROSS APPLY (
                    SELECT
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGMO),
                            CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                        ) AS StartAt,
                        DATEADD(
                            SECOND,
                            DATEDIFF(SECOND, CAST('00:00:00' AS TIME), C.TGDONG),
                            DATEADD(
                                DAY, CASE WHEN C.TGDONG <= C.TGMO THEN 1 ELSE 0 END,
                                CAST(CAST(C.NGAYLAM AS DATE) AS DATETIME2)
                            )
                        ) AS EndAt
                ) T
                LEFT JOIN dbo.LAMCA L ON L.MACA = C.MACA
                WHERE
                    @Period = 'all'
                    OR (
                        @Period = 'today'
                        AND C.NGAYLAM >= CONVERT(date, SYSDATETIME())
                        AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                    )
                    OR (
                        @Period = '7days'
                        AND C.NGAYLAM >= DATEADD(day, -6, CONVERT(date, SYSDATETIME()))
                        AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                    )
                    OR (
                        @Period = '30days'
                        AND C.NGAYLAM >= DATEADD(day, -29, CONVERT(date, SYSDATETIME()))
                        AND C.NGAYLAM < DATEADD(day, 1, CONVERT(date, SYSDATETIME()))
                    )
                GROUP BY C.MACA, C.NGAYLAM, C.SOCA, C.TGMO, C.TGDONG,
                         C.TMDAUCA, C.TMCUOICA, T.StartAt, T.EndAt
                ORDER BY C.NGAYLAM DESC, C.SOCA DESC
            """, period)
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_shift_roster(self, shift_id):
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT NV.MANV, NV.TENNV, NV.VAITRO, NV.SDT
                FROM dbo.LAMCA LC
                INNER JOIN dbo.NHAN_VIEN NV ON NV.MANV = LC.MANV
                WHERE LC.MACA = ?
                ORDER BY NV.MANV
            """, int(shift_id))
            return [tuple(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def delete_shift(self, shift_id):
        """Chỉ xóa ca chưa bắt đầu, chưa chốt và chưa phát sinh hóa đơn."""
        conn = self._connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT
                    CASE
                        WHEN TGMO IS NOT NULL
                         AND DATEADD(
                                SECOND,
                                DATEDIFF(SECOND, CAST('00:00:00' AS TIME), TGMO),
                                CAST(CAST(NGAYLAM AS DATE) AS DATETIME2)
                             ) > SYSDATETIME()
                         AND TMCUOICA IS NULL
                        THEN 1 ELSE 0
                    END
                FROM dbo.CA_LAM_VIEC WITH (UPDLOCK, HOLDLOCK)
                WHERE MACA = ?
            """, int(shift_id))
            row = cursor.fetchone()
            if row is None:
                raise LookupError("Ca làm việc không còn tồn tại.")
            if not bool(row[0]):
                raise ValueError(
                    "Chỉ được xóa ca chưa bắt đầu và chưa chốt tiền cuối ca."
                )

            cursor.execute("""
                SELECT TOP 1 MAHD
                FROM dbo.HOA_DON WITH (UPDLOCK, HOLDLOCK)
                WHERE MACA = ?
            """, int(shift_id))
            if cursor.fetchone() is not None:
                raise ValueError(
                    "Không thể xóa ca vì đã có hóa đơn liên kết với ca này."
                )

            # LAMCA tu dong duoc xoa boi FK ON DELETE CASCADE khi xoa ca.
            # Quan ly khong can va khong duoc cap quyen DELETE truc tiep tren LAMCA.
            cursor.execute("DELETE FROM dbo.CA_LAM_VIEC WHERE MACA = ?", int(shift_id))
            if cursor.rowcount != 1:
                raise RuntimeError("Không thể xóa ca làm việc đã chọn.")
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

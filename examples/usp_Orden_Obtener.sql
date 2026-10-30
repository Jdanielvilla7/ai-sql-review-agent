CREATE PROCEDURE dbo.sp_Orden_Obtener
    @ClienteId NVARCHAR(MAX)
AS
BEGIN
    SELECT *
    FROM dbo.Orden WITH (NOLOCK)
    WHERE ISNULL(ClienteId, 0) = ISNULL(@ClienteId, 0)
END

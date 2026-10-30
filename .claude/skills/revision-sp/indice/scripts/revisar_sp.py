#!/usr/bin/env python3
"""
Chequeos estáticos de Stored Procedures T-SQL contra los política SQL Server de referencia v1.0.

Detecta de forma mecánica las violaciones que no requieren juicio, para que la
revisión manual se concentre en lo que sí lo requiere (equivalencias, determinismo,
índices, lógica de negocio).

Uso:
    python revisar_sp.py archivo.sql [otro.sql | carpeta/ ...] [--json]

Cada hallazgo indica:
    severidad : CRITICO | INCUMPLE | RECOMENDADO
    certeza   : alta (patrón inequívoco) | heuristica (confirmar leyendo el código)
    item      : número del checklist en references/checklist.md

Limitaciones conocidas: es un analizador léxico, no un parser completo de T-SQL.
Comentarios y literales de texto se ignoran (por eso el SQL dinámico armado dentro
de cadenas no se analiza aquí: revísalo a mano). Un "sin hallazgos" NO equivale a
"aprobado": siempre falta la revisión manual.
"""
import json
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Lectura con detección de codificación (SSMS suele guardar en UTF-16 LE)
# --------------------------------------------------------------------------- #

def leer(path):
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le"), "UTF-16 LE (BOM)"
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be"), "UTF-16 BE (BOM)"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8"), "UTF-8 con BOM"
    try:
        return raw.decode("utf-8"), "UTF-8"
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace"), "Windows-1252 / Latin-1"


# --------------------------------------------------------------------------- #
# Enmascarado: quita comentarios y contenido de cadenas conservando saltos de
# línea, para que los números de línea sigan siendo válidos.
# --------------------------------------------------------------------------- #

def enmascarar(src):
    out, comentarios = [], []
    i, n, linea = 0, len(src), 1
    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "-" and nxt == "-":                       # comentario de línea
            j = src.find("\n", i)
            j = n if j == -1 else j
            comentarios.append((linea, src[i + 2:j], "linea"))
            out.append(" " * (j - i))
            i = j
        elif c == "/" and nxt == "*":                     # comentario de bloque (anidable)
            depth, j, ini = 1, i + 2, linea
            while j < n and depth:
                if src.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif src.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            bloque = src[i:j]
            comentarios.append((ini, bloque, "bloque"))
            out.append(re.sub(r"[^\n]", " ", bloque))
            linea += bloque.count("\n")
            i = j
        elif c == "'":                                    # literal de texto
            j = i + 1
            while j < n:
                if src[j] == "'" and j + 1 < n and src[j + 1] == "'":
                    j += 2
                elif src[j] == "'":
                    break
                else:
                    j += 1
            lit = src[i:j + 1]
            out.append("'" + re.sub(r"[^\n]", " ", lit[1:-1]) + "'")
            linea += lit.count("\n")
            i = j + 1
        elif c in "[\"":                                  # identificador delimitado
            cierre = "]" if c == "[" else '"'
            j = src.find(cierre, i + 1)
            j = n if j == -1 else j
            out.append(src[i + 1:j])                      # sin delimitadores
            linea += src[i + 1:j].count("\n")
            i = j + 1
        else:
            if c == "\n":
                linea += 1
            out.append(c)
            i += 1
    return "".join(out), comentarios


# --------------------------------------------------------------------------- #
# Tokenizador mínimo y división en sentencias a nivel 0
# --------------------------------------------------------------------------- #

TOKEN = re.compile(r"@@?\w+|#{1,2}\w+|\w+|'[^']*'|<>|!=|>=|<=|[(),;.*=<>+\-/]|\S", re.S)

INICIO_SENTENCIA = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "DECLARE", "SET", "IF", "ELSE", "WHILE",
    "EXEC", "EXECUTE", "BEGIN", "END", "RETURN", "CREATE", "ALTER", "DROP",
    "TRUNCATE", "COMMIT", "ROLLBACK", "THROW", "RAISERROR", "PRINT", "GO", "SELECT",
    "WITH", "FETCH", "OPEN", "CLOSE", "DEALLOCATE", "GOTO", "WAITFOR",
}


def tokenizar(masked):
    toks, linea, pos = [], 1, 0
    for m in TOKEN.finditer(masked):
        linea += masked.count("\n", pos, m.start())
        pos = m.start()
        toks.append((m.group(0), m.group(0).upper(), linea))
    return toks


def sentencias(toks):
    """Divide en sentencias de nivel 0. Devuelve listas de (tok, TOK, linea, depth, etiqueta_paren)."""
    res, actual = [], []
    depth, pila, case_depth = 0, [], 0
    inicio = None
    for idx, (t, T, ln) in enumerate(toks):
        prev = toks[idx - 1][1] if idx else ""
        nuevo = False
        if depth == 0 and case_depth == 0 and T in INICIO_SENTENCIA:
            nuevo = True
            if T == "SELECT" and (inicio in ("INSERT", "WITH") and not any(x[1] == "SELECT" for x in actual)):
                nuevo = False
            if T == "SELECT" and prev in ("UNION", "ALL", "EXCEPT", "INTERSECT", "("):
                nuevo = False
            if T == "SET" and inicio in ("UPDATE", "MERGE"):
                nuevo = False
            if T == "WITH" and idx + 1 < len(toks) and toks[idx + 1][0] == "(":
                nuevo = False                          # hint WITH (NOLOCK)
            if T in ("ELSE", "END") and case_depth:
                nuevo = False
            if T == "EXEC" and inicio == "INSERT":
                nuevo = False
        if t == ";" and depth == 0:
            if actual:
                res.append(actual)
            actual, inicio = [], None
            continue
        if nuevo and actual:
            res.append(actual)
            actual = []
        if nuevo or not actual:
            inicio = T
        if T == "CASE":
            case_depth += 1
        elif T == "END" and case_depth:
            case_depth -= 1
        etiqueta = pila[-1] if pila else None
        actual.append((t, T, ln, depth, etiqueta))
        if t == "(":
            etiqueta_nueva = "over" if prev in ("OVER", "GROUP") else "paren"
            pila.append(etiqueta_nueva)
            depth += 1
        elif t == ")" and depth:
            pila.pop()
            depth -= 1
    if actual:
        res.append(actual)
    return res


# --------------------------------------------------------------------------- #
# Reglas
# --------------------------------------------------------------------------- #

class Hallazgos:
    def __init__(self):
        self.items = []

    def add(self, item, severidad, certeza, linea, regla, detalle):
        self.items.append(dict(item=item, severidad=severidad, certeza=certeza,
                               linea=linea, regla=regla, detalle=detalle))


def linea_de(masked, pos):
    return masked.count("\n", 0, pos) + 1


def analizar(path):
    src, codificacion = leer(path)
    masked, comentarios = enmascarar(src)
    toks = tokenizar(masked)
    sents = sentencias(toks)
    H = Hallazgos()
    U = masked.upper()

    tiene_proc = re.search(r"\b(CREATE|ALTER)\s+(OR\s+ALTER\s+)?PROC(EDURE)?\b", U)
    tiene_dml = re.search(r"\b(INSERT|UPDATE|DELETE|MERGE)\b(?!\s*STATISTICS)", U)

    # --- Codificación --------------------------------------------------------
    if codificacion != "UTF-8":
        H.add(5, "INCUMPLE", "alta", 1, "Codificación del archivo",
              f"El archivo está en {codificacion}; la metodología pide convertirlo a UTF-8 sin BOM.")

    # --- 1. SELECT * ---------------------------------------------------------
    for m in re.finditer(r"\bSELECT\s+(DISTINCT\s+)?(TOP\s*\(?\s*\d+\s*\)?\s*(PERCENT\s+)?)?(\w+\s*\.\s*)?\*", U):
        antes = U[max(0, m.start() - 30):m.start()]
        en_exists = re.search(r"EXISTS\s*\(\s*$", antes)
        H.add(1, "INCUMPLE", "alta", linea_de(U, m.start()), "SELECT *",
              "Dentro de EXISTS no afecta rendimiento, pero el estándar lo prohíbe: usar SELECT 1."
              if en_exists else "Especificar columnas explícitas.")
    for m in re.finditer(r",\s*\w+\s*\.\s*\*", U):
        H.add(1, "INCUMPLE", "alta", linea_de(U, m.start()), "alias.* en lista de columnas",
              "Especificar columnas explícitas.")

    # --- 2. JOIN implícito ----------------------------------------------------
    for m in re.finditer(r"\bFROM\s+[#@\w.]+(\s+(AS\s+)?(?!WHERE|INNER|LEFT|RIGHT|FULL|CROSS|JOIN|ON|WITH|GROUP|ORDER)\w+)?\s*,\s*[#@\w]", U):
        H.add(2, "INCUMPLE", "heuristica", linea_de(U, m.start()), "JOIN implícito (FROM A, B)",
              "Usar JOIN explícito con ON.")

    # --- 3. COUNT(*) > 0 -----------------------------------------------------
    for m in re.finditer(r"COUNT\s*\(\s*(\*|1)\s*\)\s*\)?\s*(>\s*0|>=\s*1|<>\s*0|!=\s*0)", U):
        H.add(3, "INCUMPLE", "alta", linea_de(U, m.start()), "COUNT(*) > 0 para existencia",
              "Usar IF EXISTS (SELECT 1 ...).")
    for m in re.finditer(r"\bIF\s*\(\s*SELECT\s+COUNT\s*\(", U):
        H.add(3, "INCUMPLE", "heuristica", linea_de(U, m.start()), "IF (SELECT COUNT(...)) ...",
              "Si solo verifica existencia, usar IF EXISTS.")

    # --- Contexto de cláusula para ISNULL / funciones sobre columnas ---------
    CLAUSULAS = {"SELECT", "FROM", "JOIN", "WHERE", "ON", "HAVING", "GROUP", "ORDER", "SET", "VALUES", "INTO"}
    FUNC_NO_SARG = {"UPPER", "LOWER", "LTRIM", "RTRIM", "TRIM", "SUBSTRING", "LEFT", "RIGHT",
                    "YEAR", "MONTH", "DAY", "CONVERT", "CAST", "DATEPART", "DATEDIFF", "REPLACE"}
    for s in sents:
        clausula_por_nivel = {}
        for k, (t, T, ln, d, et) in enumerate(s):
            if T in CLAUSULAS:
                clausula_por_nivel[d] = T
                for dd in [x for x in clausula_por_nivel if x > d]:
                    del clausula_por_nivel[dd]
            sig = s[k + 1][0] if k + 1 < len(s) else ""
            sig2 = s[k + 2][0] if k + 2 < len(s) else ""
            # Buscar la cláusula vigente más cercana (mismo nivel o superior)
            cl = None
            for nivel in range(d, -1, -1):
                if nivel in clausula_por_nivel:
                    cl = clausula_por_nivel[nivel]
                    break
            if T == "ISNULL" and sig == "(" and cl in ("WHERE", "ON", "HAVING"):
                H.add(4, "INCUMPLE", "heuristica", ln, f"ISNULL() en predicado {cl}",
                      "Inhabilita índices. Reescribir con IS NULL / IS NOT NULL + comparación. "
                      "OJO: verificar equivalencia del resultado (ver equivalencias-determinismo.md).")
            if T in FUNC_NO_SARG and sig == "(" and cl in ("WHERE", "ON") and not sig2.startswith("@"):
                # CONVERT(tipo, col): el primer arg es el tipo
                if T == "CONVERT" and k + 4 < len(s) and s[k + 4][0].startswith("@"):
                    continue
                H.add(None, "RECOMENDADO", "heuristica", ln, f"{T}() sobre columna en {cl}",
                      "Predicado posiblemente no SARGable: impide seek sobre el índice.")

    # --- 5. Código comentado --------------------------------------------------
    patron_codigo = re.compile(r"^\s*(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|INNER\s+JOIN|LEFT\s+JOIN|JOIN|EXEC|DECLARE|SET\s+@|AND\s+\w+\s*=|GROUP\s+BY|ORDER\s+BY)\b", re.I)
    lineas_cod = []
    for ln, txt, tipo in comentarios:
        for off, l in enumerate(txt.split("\n")):
            if patron_codigo.search(l.lstrip("/*- ")):
                lineas_cod.append(ln + off)
    if lineas_cod:
        H.add(5, "INCUMPLE", "heuristica", lineas_cod[0], "Código comentado",
              f"{len(lineas_cod)} línea(s) de comentario parecen código (líneas {', '.join(map(str, lineas_cod[:10]))}"
              f"{'…' if len(lineas_cod) > 10 else ''}). Eliminar salvo justificación; el historial va en control de versiones.")

    # --- 6. WHERE 1=1 (fuera de cadenas: el dinámico se revisa a mano) -------
    for m in re.finditer(r"\bWHERE\s+(1\s*=\s*1|0\s*=\s*0)\b", U):
        H.add(6, "INCUMPLE", "alta", linea_de(U, m.start()), "WHERE 1=1 / 0=0 estático", "Eliminar.")

    # --- 10. SET NOCOUNT ON y TRY/CATCH --------------------------------------
    if tiene_proc:
        ln_proc = linea_de(U, tiene_proc.start())
        if not re.search(r"\bSET\s+NOCOUNT\s+ON\b", U):
            H.add(10, "INCUMPLE", "alta", ln_proc, "Falta SET NOCOUNT ON", "Agregar al inicio del cuerpo del SP.")
        if not re.search(r"\bBEGIN\s+TRY\b", U):
            H.add(10, "CRITICO" if tiene_dml else "INCUMPLE", "alta", ln_proc, "Falta BEGIN TRY / BEGIN CATCH",
                  "El SP modifica datos sin manejo de errores." if tiene_dml else "Encapsular en TRY/CATCH.")

    # --- 11. SQL dinámico ----------------------------------------------------
    for m in re.finditer(r"\bEXEC(UTE)?\s*\(\s*@", U):
        H.add(11, "CRITICO", "alta", linea_de(U, m.start()), "EXEC(@sql)",
              "SQL dinámico sin parametrizar. Usar sp_executesql con @params.")
    for m in re.finditer(r"\bSP_EXECUTESQL\s+(@\w+)", masked, re.I):
        var = m.group(1)
        resto = masked[m.end():m.end() + 60]
        if not re.match(r"\s*,", resto):
            H.add(11, "INCUMPLE", "heuristica", linea_de(U, m.start()), "sp_executesql sin parámetros",
                  f"Se ejecuta {var} sin lista de @params: verificar que no se concatenaron valores.")
        for a in re.finditer(rf"\b(SET|SELECT)\s+{re.escape(var)}\s*\+?=\s*(.*?)(?=\bSET\b|\bEXEC|\bIF\b|\bDECLARE\b|;|$)", masked, re.S | re.I):
            rhs = a.group(2)
            concat = [v for v in re.findall(r"@\w+", rhs) if v.lower() != var.lower() and re.search(rf"(\+\s*{re.escape(v)}\b|\b{re.escape(v)}\s*\+)", rhs)]
            if concat:
                H.add(11, "CRITICO", "heuristica", linea_de(U, a.start()), "Concatenación en SQL dinámico",
                      f"{var} concatena {', '.join(sorted(set(concat)))}. Si es input de usuario, pasarlo como "
                      "parámetro; si es un identificador, validar contra lista blanca y usar QUOTENAME.")

    # --- 12. Transacciones ---------------------------------------------------
    if re.search(r"\bBEGIN\s+TRAN(SACTION)?\b", U):
        ln_t = linea_de(U, re.search(r"\bBEGIN\s+TRAN(SACTION)?\b", U).start())
        if not re.search(r"\bBEGIN\s+TRY\b", U):
            H.add(12, "CRITICO", "alta", ln_t, "Transacción fuera de TRY/CATCH",
                  "Ante error la transacción puede quedar abierta.")
        catch = re.search(r"\bBEGIN\s+CATCH\b(.*?)\bEND\s+CATCH\b", U, re.S)
        if catch:
            cuerpo = catch.group(1)
            if "ROLLBACK" not in cuerpo:
                H.add(12, "CRITICO", "alta", linea_de(U, catch.start()), "CATCH sin ROLLBACK",
                      "Agregar IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION.")
            elif "@@TRANCOUNT" not in cuerpo:
                H.add(12, "INCUMPLE", "alta", linea_de(U, catch.start()), "ROLLBACK sin verificar @@TRANCOUNT",
                      "Usar IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION.")
            if not re.search(r"\b(THROW|RAISERROR)\b", cuerpo):
                H.add(None, "INCUMPLE", "alta", linea_de(U, catch.start()), "CATCH silencia el error",
                      "El error no se relanza (THROW): quien llama no se entera del fallo.")
        if not re.search(r"\bCOMMIT\b", U):
            H.add(12, "CRITICO", "alta", ln_t, "BEGIN TRAN sin COMMIT", "Revisar cierre de la transacción.")

    # --- 14. NOLOCK / READ UNCOMMITTED ---------------------------------------
    for m in re.finditer(r"\(\s*NOLOCK\s*\)|\bREADUNCOMMITTED\b|\bISOLATION\s+LEVEL\s+READ\s+UNCOMMITTED\b", U):
        H.add(14, "CRITICO" if tiene_dml else "INCUMPLE", "alta", linea_de(U, m.start()), "NOLOCK / READ UNCOMMITTED",
              "El SP modifica datos: NOLOCK prohibido en lógica de negocio." if tiene_dml
              else "Solo permitido en lectura no crítica con justificación documentada. Preferir RCSI.")

    # --- 16. Naming del SP ---------------------------------------------------
    for m in re.finditer(r"\b(?:CREATE|ALTER)\s+(?:OR\s+ALTER\s+)?PROC(?:EDURE)?\s+(?:(\w+)\s*\.\s*)?(\w+)", masked, re.I):
        nombre = m.group(2)
        ln = linea_de(masked, m.start())
        if nombre.lower().startswith("sp_"):
            H.add(16, "INCUMPLE", "alta", ln, f"Prefijo sp_ en '{nombre}'",
                  "Reservado para sistema (SQL Server busca primero en master). Usar usp_<Entidad>_<Accion>.")
        elif not re.match(r"^usp_[A-Z][A-Za-z0-9]*_[A-Z][A-Za-z0-9]*$", nombre):
            H.add(16, "INCUMPLE", "alta", ln, f"Nombre '{nombre}' no sigue usp_<Entidad>_<Accion>",
                  "Ej.: usp_Factura_Crear, usp_Pedido_ObtenerPorCliente.")
        if not m.group(1):
            H.add(None, "RECOMENDADO", "alta", ln, "SP sin esquema explícito", "Calificar con esquema (dbo.usp_...).")

    # --- 17. Tipos de dato a evitar ------------------------------------------
    for m in re.finditer(r"(@\w+|^\s*#?\w+)\s+(AS\s+)?(TEXT|NTEXT|IMAGE|FLOAT|REAL|DATETIME|SMALLDATETIME)\b", U, re.M):
        H.add(17, "INCUMPLE", "heuristica", linea_de(U, m.start()), f"Tipo {m.group(3)}",
              {"FLOAT": "Montos: DECIMAL(18,4).", "REAL": "Montos: DECIMAL(18,4).",
               "DATETIME": "Usar DATETIME2(3) o DATE.", "SMALLDATETIME": "Usar DATETIME2(3) o DATE."}
              .get(m.group(3), "Tipo obsoleto: NVARCHAR(MAX) / VARBINARY(MAX)."))
    if tiene_proc:
        cab = re.search(r"\bPROC(EDURE)?\b(.*?)\bAS\b", masked, re.S | re.I)
        if cab:
            for m in re.finditer(r"(@\w+)\s+N?VARCHAR\s*\(\s*MAX\s*\)", cab.group(2), re.I):
                H.add(None, "INCUMPLE", "heuristica", linea_de(U, cab.start(2) + m.start()),
                      f"Parámetro {m.group(1)} como (N)VARCHAR(MAX)",
                      "Usar longitud precisa si el dominio es limitado.")

    # --- 9. Índice en #Temp antes del INSERT masivo --------------------------
    for m in re.finditer(r"\bCREATE\s+(UNIQUE\s+)?(CLUSTERED\s+|NONCLUSTERED\s+)?INDEX\s+\w+\s+ON\s+(#\w+)", U):
        tabla = m.group(3)
        ins = re.search(rf"\bINSERT\s+(INTO\s+)?{re.escape(tabla)}\b", U)
        if ins and ins.start() > m.start():
            H.add(9, "INCUMPLE", "alta", linea_de(U, m.start()), f"Índice sobre {tabla} antes del INSERT",
                  "Crear el índice después de la carga masiva.")

    # --- 31. Índices filtrados sin ANSI_NULLS / QUOTED_IDENTIFIER -----------
    if re.search(r"\bCREATE\s+[\w\s]*INDEX\b[^;]*?\)\s*(INCLUDE\s*\([^)]*\)\s*)?WHERE\b", U):
        for opt in ("ANSI_NULLS", "QUOTED_IDENTIFIER"):
            if not re.search(rf"\bSET\s+{opt}\s+ON\b", U):
                H.add(31, "INCUMPLE", "alta", 1, f"Falta SET {opt} ON con índice filtrado",
                      "Sin esto el DML sobre la tabla falla con error 1934.")

    # --- Reglas por sentencia -------------------------------------------------
    for s in sents:
        if not s:
            continue
        T0 = s[0][1]
        cero = [x for x in s if x[3] == 0]
        nivel0 = [x[1] for x in cero]
        tiene = lambda w: w in nivel0
        ob = [x for i, x in enumerate(cero) if x[1] == "ORDER" and i + 1 < len(cero) and cero[i + 1][1] == "BY"]
        # 25. ORDER BY en INSERT...SELECT / SELECT...INTO (sin TOP/OFFSET)
        if ob and not tiene("TOP") and not tiene("OFFSET"):
            if T0 == "INSERT" and tiene("SELECT"):
                H.add(25, "INCUMPLE", "alta", ob[0][2], "ORDER BY en INSERT ... SELECT",
                      "No define el orden físico del destino; solo agrega un Sort. Eliminar.")
            elif T0 in ("SELECT", "WITH") and tiene("INTO"):
                H.add(25, "INCUMPLE", "alta", ob[0][2], "ORDER BY en SELECT ... INTO",
                      "No define el orden físico del destino; solo agrega un Sort. Eliminar.")
        # 26. UNION ALL sin ORDER BY final
        if tiene("UNION") and not ob and T0 in ("SELECT", "WITH") and not tiene("INTO"):
            ln = next(x[2] for x in cero if x[1] == "UNION")
            H.add(26, "INCUMPLE", "heuristica", ln, "UNION sin ORDER BY final",
                  "El orden entre ramas no está garantizado. Agregar bandera _kind y ORDER BY final.")
        # TOP sin ORDER BY (determinismo)
        for i, x in enumerate(s):
            if x[1] == "TOP":
                d = x[3]
                mismo = [y for y in s if y[3] == d]
                j = mismo.index(x)
                tiene_ob = any(mismo[q][1] == "ORDER" and q + 1 < len(mismo) and mismo[q + 1][1] == "BY" for q in range(j, len(mismo)))
                if not tiene_ob:
                    H.add(27, "INCUMPLE", "alta", x[2], "TOP sin ORDER BY",
                          "Resultado no determinista: qué filas devuelve depende del plan.")
        # ORDER BY dentro de subconsulta / CTE (no OVER, no WITHIN GROUP)
        for i, x in enumerate(s):
            if x[1] == "ORDER" and i + 1 < len(s) and s[i + 1][1] == "BY" and x[3] > 0 and x[4] != "over":
                H.add(13, "INCUMPLE", "heuristica", x[2], "ORDER BY en subconsulta o CTE",
                      "Prohibido en subconsultas/CTEs intermedias. Si acompaña a TOP por diseño, confirmar determinismo.")

    # --- Catch-all queries --------------------------------------------------
    if not re.search(r"\bOPTION\s*\([^)]*RECOMPILE", U):
        for m in re.finditer(r"\(\s*@\w+\s*(IS\s+NULL|=\s*-?\d+|=\s*''|=\s*@\w+)\s+OR\s+[\w.]+\s*(=|LIKE|>=|<=|IN)", U):
            H.add(None, "RECOMENDADO", "heuristica", linea_de(U, m.start()), "Catch-all query (@P IS NULL OR col = @P)",
                  "Plan único que sirve mal a todos los valores. OPTION (RECOMPILE) si es de baja frecuencia; "
                  "sp_executesql parametrizado si es de alta frecuencia.")

    # --- Cursores ------------------------------------------------------------
    for m in re.finditer(r"\bDECLARE\s+\w+\s+(INSENSITIVE\s+|SCROLL\s+)?CURSOR\b", U):
        H.add(None, "RECOMENDADO", "alta", linea_de(U, m.start()), "Cursor",
              "Evaluar reemplazo por operación basada en conjuntos.")

    # --- IN (SELECT ...) ------------------------------------------------------
    for m in re.finditer(r"\bNOT\s+IN\s*\(\s*SELECT\b", U):
        H.add(None, "INCUMPLE", "heuristica", linea_de(U, m.start()), "NOT IN (SELECT ...)",
              "Si la subconsulta puede devolver NULL, NOT IN devuelve cero filas. Preferir NOT EXISTS "
              "(verificar equivalencia antes de cambiar).")

    # --- Encabezado de comentario --------------------------------------------
    if tiene_proc:
        pre = [txt for ln, txt, _ in comentarios]
        texto = " ".join(pre).lower()
        faltan = [c for c, pat in (("autor", r"autor"), ("fecha", r"fecha"), ("descripción", r"descripci"),
                                   ("historial", r"historial|cambios|modificaci")) if not re.search(pat, texto)]
        if faltan:
            H.add(None, "INCUMPLE", "alta", 1, "Encabezado incompleto",
                  f"Falta en el comentario de encabezado: {', '.join(faltan)}.")

    # --- Palabras reservadas en minúscula ------------------------------------
    reservadas = r"\b(select|from|where|inner|left|right|join|on|and|or|insert|into|update|delete|set|declare|begin|end|if|else|exists|group|order|by|having|union|all|as|case|when|then|null|not|is|in|exec|return|commit|rollback|transaction|tran)\b"
    minus = [linea_de(masked, m.start()) for m in re.finditer(reservadas, masked)]
    if minus:
        H.add(None, "INCUMPLE", "alta", minus[0], "Palabras reservadas en minúscula",
              f"{len(minus)} ocurrencia(s), p. ej. líneas {', '.join(map(str, sorted(set(minus))[:8]))}. "
              "El estándar exige MAYÚSCULAS.")

    return codificacion, sorted(H.items, key=lambda h: (["CRITICO", "INCUMPLE", "RECOMENDADO"].index(h["severidad"]), h["linea"]))


MANUALES = [
    (7, "PK/FK con el mismo tipo de dato"), (8, "Toda FK con índice non-clustered"),
    (13, "ORDER BY final respaldado por índice"), (15, "Validaciones de front-end"),
    (18, "Funciones escalares en SELECT masivo"), (21, "Refactors demuestran equivalencia"),
    (22, "Pre-agregación solo con funciones distributivas"), (23, "Conversiones que pueden fallar usan TRY_CAST"),
    (24, "BETWEEN → rango semiabierto declarado"), (27, "TOP ordena por columna que el WHERE no fija"),
    (28, "Funciones de ventana con desempate único"), (29, "Clave clustered no aparece en INCLUDE"),
    (30, "Índice filtrado no clavea la columna que filtra"), (32, "Índice propuesto con consumidor verificado"),
    (33, "Todas las definiciones del objeto revisadas (PROD/QA, init)"),
    (None, "SQL dinámico construido dentro de cadenas (no analizado por el script)"),
]


def main(argv):
    as_json = "--json" in argv
    rutas = [a for a in argv if a != "--json"]
    if not rutas:
        print(__doc__)
        return 2
    archivos = []
    for r in rutas:
        p = Path(r)
        archivos += sorted(p.rglob("*.sql")) if p.is_dir() else [p]
    salida = {}
    for f in archivos:
        cod, hall = analizar(f)
        salida[str(f)] = {"codificacion": cod, "hallazgos": hall}
    if as_json:
        print(json.dumps(salida, ensure_ascii=False, indent=2))
        return 0
    for f, d in salida.items():
        h = d["hallazgos"]
        cnt = {s: sum(1 for x in h if x["severidad"] == s) for s in ("CRITICO", "INCUMPLE", "RECOMENDADO")}
        print(f"\n## {f}  (codificación: {d['codificacion']})")
        print(f"CRITICO: {cnt['CRITICO']} | INCUMPLE: {cnt['INCUMPLE']} | RECOMENDADO: {cnt['RECOMENDADO']}\n")
        if h:
            print("| Sev. | Línea | Ítem | Regla | Certeza | Detalle |")
            print("|---|---|---|---|---|---|")
            for x in h:
                print(f"| {x['severidad']} | {x['linea']} | {x['item'] or '-'} | {x['regla']} | {x['certeza']} | {x['detalle']} |")
        else:
            print("Sin hallazgos automáticos (esto NO equivale a aprobado).")
    print("\n### Pendiente de revisión manual (el script no puede verificarlo)")
    for i, t in MANUALES:
        print(f"- [{i or '-'}] {t}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

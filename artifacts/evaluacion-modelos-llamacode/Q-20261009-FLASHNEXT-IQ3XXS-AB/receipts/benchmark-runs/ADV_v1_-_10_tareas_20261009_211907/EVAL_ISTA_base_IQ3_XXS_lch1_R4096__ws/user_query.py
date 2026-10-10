"""build_user_query: consulta parametrizada (placeholders ?) sin interpolar valores.

filters: dict opcional con name, email y/o active.
Devuelve (sql, params) con los placeholders ? y params en el mismo orden que las
clausulas, siempre en el orden name, email, active.

  name   -> name LIKE ?   con param '%' + valor + '%'
  email  -> email LIKE ?  con param '%' + valor + '%'
  active -> active = ?    con param bool

La consulta base es SELECT id, name, email, active FROM users y no se modifica.
Rechaza con ValueError: campos desconocidos, tipos incorrectos y strings con NUL.
"""

BASE_SQL = "SELECT id, name, email, active FROM users"

# Orden fijo de clausulas: name, email, active.
CLAUSE_ORDER = ("name", "email", "active")

LIKE_FIELDS = ("name", "email")


def build_user_query(filters=None):
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        raise ValueError("filters debe ser un dict opcional de filtros")

    unknown = sorted(key for key in filters if key not in CLAUSE_ORDER)
    if unknown:
        raise ValueError("campos desconocidos en filters: {}".format(unknown))

    clauses = []
    params = []

    for field in CLAUSE_ORDER:
        if field not in filters:
            continue

        value = filters[field]

        if field in LIKE_FIELDS:
            if not isinstance(value, str):
                raise ValueError(
                    "{} debe ser un string: {!r}".format(field, value))
            if "\x00" in value:
                raise ValueError("{} no puede contener NUL".format(field))
            clauses.append("{} LIKE ?".format(field))
            params.append("%" + value + "%")
        else:  # active
            if not isinstance(value, bool):
                raise ValueError(
                    "active debe ser un bool: {!r}".format(value))
            clauses.append("active = ?")
            params.append(value)

    sql = BASE_SQL
    if clauses:
        sql = sql + " WHERE " + " AND ".join(clauses)

    return sql, params

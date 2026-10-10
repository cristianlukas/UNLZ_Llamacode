_BASE_SQL = "SELECT id, name, email, active FROM users"
_ALLOWED = ("name", "email", "active")
def build_user_query(filters):
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be a dict or None")
    unknown = sorted(set(filters) - set(_ALLOWED))
    if unknown:
        raise ValueError("unknown filter field(s): " + ", ".join(unknown))
    clauses = []
    params = []
    for field in ("name", "email"):
        if field in filters:
            value = filters[field]
            if not isinstance(value, str):
                raise ValueError(field + " filter must be a string")
            if "\x00" in value:
                raise ValueError(field + " filter must not contain a NUL byte")
            clauses.append(field + " LIKE ?")
            params.append("%" + value + "%")
    if "active" in filters:
        value = filters["active"]
        if not isinstance(value, bool):
            raise ValueError("active filter must be a bool")
        clauses.append("active = ?")
        params.append(value)
    sql = _BASE_SQL
    if clauses:
        sql = sql + " WHERE " + " AND ".join(clauses)
    return sql, params
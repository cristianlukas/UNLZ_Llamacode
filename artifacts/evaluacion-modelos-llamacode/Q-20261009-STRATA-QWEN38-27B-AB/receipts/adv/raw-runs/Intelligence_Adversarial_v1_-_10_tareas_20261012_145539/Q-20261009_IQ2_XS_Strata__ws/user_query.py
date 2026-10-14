"""Parameterized user query builder (no value interpolation in SQL)."""

BASE_QUERY = "SELECT id, name, email, active FROM users"
ALLOWED_FIELDS = ("name", "email", "active")


def build_user_query(filters):
    """Return (sql, params) for the users table with parameterized clauses.

    filters is an optional dict with 'name', 'email' (contains search ->
    '%value%') and 'active' (bool, equality). Clauses are emitted in the
    order name, email, active, with '?' placeholders and params in the same
    order. The base query is never changed and values are never interpolated
    into SQL. Raises ValueError on unknown fields, wrong types or NUL bytes.
    """
    if filters is None:
        filters = {}
    if not isinstance(filters, dict):
        raise ValueError("filters must be a dict")

    unknown = [key for key in filters if key not in ALLOWED_FIELDS]
    if unknown:
        raise ValueError(f"unknown filter field(s): {sorted(unknown)}")

    clauses = []
    params = []

    for field in ALLOWED_FIELDS:
        if field not in filters:
            continue
        value = filters[field]

        if field == "active":
            if not isinstance(value, bool):
                raise ValueError("active must be a bool")
            clauses.append("active = ?")
            params.append(value)
        else:
            if not isinstance(value, str):
                raise ValueError(f"{field} must be a string")
            if "\x00" in value:
                raise ValueError(f"{field} must not contain NUL bytes")
            clauses.append(f"{field} LIKE ?")
            params.append("%" + value + "%")

    sql = BASE_QUERY
    if clauses:
        sql = BASE_QUERY + " WHERE " + " AND ".join(clauses)
    return sql, params

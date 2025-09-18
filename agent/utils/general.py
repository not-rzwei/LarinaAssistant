def parse_param(param: str) -> str:
    if param and len(param) >= 2 and param[0] == param[-1] and param[0] in ("'", '"'):
        return param[1:-1]
    return param

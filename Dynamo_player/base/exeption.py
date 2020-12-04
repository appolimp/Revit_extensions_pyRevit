class ScriptError(Exception):
    pass


class SheetsNotSelected(ScriptError):
    pass


class ElemNotFound(ScriptError):
    pass

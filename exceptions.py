
class UnknownTask(ValueError):
    pass

class UnknownCommand(ValueError):
    pass

class MissingVariableInSettings(KeyError):
    pass

class ImmutableObject(TypeError):
    pass

class PycroWarning(Exception):
    pass

class NothingToDo(PycroWarning):
    pass

class GroupContainsItself(ValueError):
    pass

class SyntaxError(ValueError):
    pass

class InvalidCommand(ValueError):
   pass

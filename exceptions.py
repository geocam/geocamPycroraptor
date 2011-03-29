# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

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

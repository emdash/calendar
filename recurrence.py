class Node(object):

    def __init__(self, *children):
        self.children = children

    def __eq__(self, other):
        return (type(self) == type(other)) and (self.children == other.children)

    def __str__(self):
        return self.__class__.__name__ + "(" + \
            ", ".join((str(c) for c in self.children)) + ')'

class DateSet(Node):

    pass

class Daily(Node):
    
    pass

class Weekly(Node):

    pass

class Monthly(Node):

    pass

class NthWeekday(Node):

    pass

class And(Node):

    pass

class Except(Node):

    def __init__(self, include, exclude):
        Node.__init__(self, include, exclude)
        self.include = include
        self.exclude = exclude
        
class From(Node):

    pass

class Until(Node):

    pass

class For(Node):

    pass

class Period(Node):

    pass

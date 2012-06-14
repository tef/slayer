import re
import operator


def lift(item):
    if isinstance(item, GrammarObject):
        return item
    else:
        return GrammarTerminal(item)

class GrammarObject(object):
    def __add__(self, item):
        return GrammarAnd(self, item)

    def __radd__(self,item):
        return GrammarAnd(item, self)

    def __or__(self, item):
        return GrammarOr(self, item)

    def __ror__(self,item):
        return GrammarOr(item, self)
    
class GrammarTerminal(GrammarObject):
    def __init__(self, terminal):
        self.terminal = terminal

    def __str__(self):
        return "'%s'"%self.terminal

    def compile(self,next):
        return Scanner(self.terminal, next) 

class GrammarNonTerminal(GrammarObject):
    pass

class GrammarRule(GrammarNonTerminal):
    def __init__(self, grammar, name):
        self.grammar = grammar
        self.name = name

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return GrammarConstraint(self,operator.lt, other)

    def __le__(self, other):
        return GrammarConstraint(self,operator.le, other)

    def __gt__(self, other):
        return GrammarConstraint(self, operator.gt, other)

    def __ge__(self, other):
        return GrammarConstraint(self, operator.ge, other)

    def __eq__(self, other):
        return GrammarConstraint(self, operator.eq, other)

    def __ne__(self, other):
        return GrammarConstraint(self,operator.ne, other)

    def __setitem__(self, index, val):
        self.grammar._add(self.name,index,val)

    def compile(self, next):
        return Predict(self.name, next)

class GrammarOr(GrammarObject):
    def __init__(self, a,b):
        self.rules = [lift(a),lift(b)]

    def __or__(self, item):
        self.rules.append(lift(item))
        return self

    def __ror__(self, item):
        self.rules.insert(0,lift(item))
        return self

    def __str__(self):
        return " | ".join(str(r) for r in self.rules)

    def compile(self, next):
        return Disjunction(r.compile(next) for r in self.rules)


class GrammarAnd(GrammarNonTerminal):
    def __init__(self, a,b):
        self.rules = [lift(a),lift(b)]

    def __add__(self, item):
        self.rules.append(lift(item))
        return self

    def __radd__(self, item):
        self.rules.insert(0,lift(item))
        return self

    def __str__(self):
        return " + ".join(str(r) for r in self.rules)

    def compile(self, next):
        for r in reversed(self.rules):
            next = r.compile(next)
        return next


class GrammarConstraint(GrammarNonTerminal):
    def __init__(self, rule, operator, precedence):
        self.rule = rule.name
        self.operator= operator
        self.precedence = precedence

    def __str__(self):
        return "%s %s %d"%(self.rule, self.operator.__name__, self.precedence)

    def compile(self, next):
        return Precedence(self.rule, self.operator, self.precedence, next)


class Grammar(object):
    def __init__(self, name):
        self._rules = []
        self._name = name

    def _add(self,name, p, val):
        self._rules.append((name,p,lift(val)))

    def __setattr__(self,name,val):
        if name.startswith('_'):
            self.__dict__[name] = val
        else:
            self._add(name,0, val)

    def __getattr__(self, name):
        return GrammarRule(self, name)

    def __str__(self):
        return ("%s\n"%self._name)+"\n".join("%s -> %s"%(name, val) for name, p,val in self._rules)

    def compile(self):
        rules = [(n,p,r.compile(Reduce(n,p))) for n,p,r in self._rules]
        return Parser(self._name, rules)


class Rule(object):
    pass

class Scanner(Rule):
    def __init__(self, string, next):
        self.string=string
        self.next = next

    def __str__(self):
        return "%s %s"%(repr(self.string), self.next)

class Predict(Rule):
    def __init__(self, name, next):
        self.name=name
        self.next=next

    def __str__(self):
        return "%s %s"%(self.name,self.next)

class Reduce(Rule):
    def __init__(self, name, p):
        self.name=name
        self.p=p

    def __str__(self):
        return "-> %s[%d] "%(self.name,self.p)

class Disjunction(Rule):
    def __init__(self, rules):
        self.rules = rules

    def __str__(self):
        return "(%s)"%(" | ".join(str(r) for r in self.rules))

class Precedence(object):
    def __init__(self, name, operator, precedence, next):
        self.name=name
        self.next=next
        self.operator = operator
        self.precedence = precedence

    def __str__(self):
        return "%s%s%d %s"%(self.name,self.operator.__name__,self.precedence, self.next)

class Parser(object):
    def __init__(self, name, rules):
        self.name = name
        self.rules = rules

    def __str__(self):
        return ("%s\n"%self.name)+"\n".join("%s -> %s"%(name, val) for name, p,val in self.rules)

g = Grammar('g')

g.item = lift("1")| "2" | "3" | "4" 
g.expr = "(" + g.expr + ")" | g.add | g.mul | g.item
g.add[20] = (g.expr < 20) + "+" + (g.expr <= 20) 
g.mul[10] = (g.expr < 10) + "*" + (g.expr <= 10) 

#g.expr[90] = g.add

print g

p = g.compile()

print p


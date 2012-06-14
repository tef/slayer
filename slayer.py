""" a parser for python """
import re
import operator
import collections


""" python objects for describing grammars """
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
        return Disjunction([r.compile(next) for r in self.rules])


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
        self.grammar._rules.add(self.name,index,val)

    def compile(self, next):
        return Predict(self.name, next)

    def parser(self):
        return make_parser(self.name, self.grammar)

class Grammar(object):
    def __init__(self):
        self._rules = ParseRules()

    def __setattr__(self,name,val):
        if name.startswith('_'):
            self.__dict__[name] = val
        else:
            self._rules.add(name,0, val)

    def __getattr__(self, name):
        if name.startswith('_'):
            return self.__dict__[name]

        return GrammarRule(self, name)

    def __str__(self):
        return str(self._rules)

""" Parse rules built from the grammar """
class ParseRules(object):
    def __init__(self):
        self.rules = []
    
    def add(self, name, p, val):
        print name, p,val
        self.rules.append((name,p,lift(val).compile(Reduce(name,p))))

    def __str__(self):
        return "\n".join("%s -> %s"%(name, val) for name, p,val in self.rules)

    def predict(self, name, precedence=None):
        """ todo do all left corner shit """
        if precedence is None:
            return [rule for n,p,rule in self.rules if n == name]
        else:
            return [rule for n,p,rule in self.rules if n == name and precedence(p)]

parseitem = collections.namedtuple('parseitem','start rule')

def make_parser(final, grammar):

    """An earley recognizer loosely based on the Aretz Model,
       and the driver loop found in the aycock/horspool earley
       parser


       An earley parser uses sets of dotted items (zippers over grammar rules)
       and uses breath first search over these by means of three actions:

       scanning: move the dot across a terminal

       complete: if dot at end, find earlier kernel items which it completes
                 and add them to current set
       predict: if dot before non-terminal, add new earley items to current
                set for non-terminal 
    """

    rules = grammar._rules

    # traditionally, earley parsers use a heterogenous list to 
    # represet the possible rules

    # instead we record the different items in different places

    #Stores the reductions made in (non-terminal, start) tuples
    #where reductions[n] = set((nt, start)...) all reductions after 
    #reading n chars 

    reductions=[None]
    
    # holds all earley items with the dot before a terminal
    # as we only need to keep the current ones 
    # i.e all shift items in (item, start) tuples
    transients = collections.deque()

    # kernel items - mid recognition
    # kernel[n] = {nt : [item, item....} 
    # all kernel items by non-terminal after reading n chars

    kernels =[{}]

    reductions = [set()]

    inbox = collections.deque()

    parser = Parser(final, rules, inbox, reductions, kernels, transients, pos=0)
    
    start = parseitem(0, final)

    for rule in rules.predict(final):
        rule.process(parser, start)

    return parser
    


class Rule(object):
    pass

class Parser(object):
    def __init__(self, final, rules, inbox,reductions, kernels, transients,pos=0):
        self.final = final
        self.rules = rules
        self.reductions = reductions
        self.kernels = kernels
        self.pos = pos
        self.inbox = inbox
        self.transients = transients

    def feed(self, string):
        for char in string:
            self.pos+=1

            for item in self.transients:
                next_rule = item.rule.advance(parser, char)
                self.inbox.append(parseitem(item.start, next_rule ))
                    
            self.transients = collections.deque()

            self.kernels.append[{}]
            self.reductions.append[set()]

            while self.inbox:
                item= self.inbox.pop()
                item.rule.process(parser, item)


    def parsed(self):
        return (final,0) in self.reductions[-1]


    def add_kernel(self, name, start, rule):
        if name not in self.kernels[-1]: 
            self.kernels[-1][name] = [parseitem(start, rule)]
            for r in self.rules.predict(name):
                self.inbox.append(parseitem(self.pos, r))

    def reduce(self, name, start):
        if (name,start) not in self.reductions[-1]:
            reductions[-1].add((start, name))
            for item in self.kernels[start][name]:
                next = item.rule.accept(nt)
                if next:
                    self.inbox.append(parseitem(start, rule))

    def scan(self, item):
        self.transients.append(item)

class Scanner(Rule):
    def __init__(self, string, next):
        self.string=string
        self.next = next

    def advance(self, char):
        if char == self.string:
            return self.next

    def __str__(self):
        return "%s %s"%(repr(self.string), self.next)

    def __hash__(self):
        return hash(self.string)*hash(self.next)

    def process(self, parser, item):
        return parser.scan(item)


class Predict(Rule):
    def __init__(self, name, next):
        self.name=name
        self.next=next

    def process(self, parser, item):
        parser.add_kernel(self.name, item.start, self.next)

    def __str__(self):
        return "%s %s"%(self.name,self.next)

    def __hash__(self):
        return hash(self.string)*hash(self.next)

class Reduce(Rule):
    def __init__(self, name, p):
        self.name=name
        self.p=p

    def __str__(self):
        return "-> %s[%d] "%(self.name,self.p)

    def __hash__(self):
        return hash(self.string)*hash(self.next)*p

    def process(self, parser, item):
        parser.reduce(self.name, item.start)

class Precedence(object):
    def __init__(self, name, operator, precedence, next):
        self.name=name
        self.next=next
        self.operator = operator
        self.precedence = precedence

    def __str__(self):
        return "%s%s%d %s"%(self.name,self.operator.__name__,self.precedence, self.next)
    def __hash__(self):
        return hash((self.name, self.rules))

class Disjunction(Rule):
    def __init__(self, rules):
        self.rules = rules

    def __str__(self):
        return "(%s)"%(" | ".join(str(r) for r in self.rules))

    def __hash__(self):
        return hash(self.rules)

    def process(self, parser, item):
        for rule in self.rules:
            rule.process(parser,item)

    def __str__(self):
        return  str(self.rules)

g = Grammar()

g.A = (g.A + "a") | "a"

p = g.A.parser()

p.feed("a")

print p
 



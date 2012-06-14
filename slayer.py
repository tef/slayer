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

    def __repr__(self):
        return "\n".join("%s -> %s"%(name, val) for name, p,val in self.rules)

    def predict(self, name, precedence=None):
        non_terminals = set()

        """ todo do all left corner shit """
        if precedence is None:
            return [rule for n,p,rule in self.rules if n == name]
        else:
            return [rule for n,p,rule in self.rules if n == name and precedence(p)]

parseitem = collections.namedtuple('parseitem','start rule')

def make_parser(start, grammar):

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

    # kernel items - mid recognition
    # kernel[n] = {nt : [item, item....} 
    # all kernel items by non-terminal after reading n chars


    reductions = [set()]

    predicted = rules.predict(start)
    final = parseitem(0, start)
    
    kernels =[{start:[]}]

    inbox = collections.deque(parseitem(0, rule) for rule in predicted)

    transients = collections.deque()


    parser = Parser(final, rules, inbox, reductions, kernels, transients, pos=0)
    

    while inbox:
        item = inbox.pop()
        item.rule.process(parser, item ,0)
        print item, parser
        

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

    def __repr__(self):
        return str(self.__dict__)

    def feed(self, string):
        for char in string:
            self.pos+=1

            for item in self.transients:
                next_rule = item.rule.advance(char)
                if next_rule:
                    self.inbox.append(parseitem(item.start, next_rule ))
                    
            self.transients = collections.deque()

            self.kernels.append({})
            self.reductions.append(set())

            while self.inbox:
                item= self.inbox.pop()
                item.rule.process(self, item, self.pos)


    def parsed(self):
        return self.final in self.reductions[-1]


    def add_kernel(self, name, rule, start, pos):
        if name not in self.kernels[pos]:
            self.kernels[pos][name] = []
            for r in self.rules.predict(name):
                self.inbox.append(parseitem(pos, r))
        self.kernels[pos][name].append(parseitem(start, rule))

    def reduce(self, name, start, pos):
        item = parseitem(start, name)
        if item not in self.reductions[pos]:
            self.reductions[pos].add(item) 
            print 'reducing'
            for item in self.kernels[start][name]:
                self.inbox.append(item)

    def scan(self, rule, start, pos):
        self.transients.append(parseitem(start, rule))

class Scanner(Rule):
    def __init__(self, string, next):
        self.string=string
        self.next = next

    def advance(self, char):
        if char == self.string:
            return self.next

    def __repr__(self):
        return "%s %s"%(repr(self.string), self.next)

    def __hash__(self):
        return hash(self.string)*hash(self.next)

    def process(self, parser, item, pos):
        return parser.scan(self, item.start, pos)


class Predict(Rule):
    def __init__(self, name, next):
        self.name=name
        self.next=next

    def process(self, parser, item, pos):
        parser.add_kernel(self.name,  self.next, item.start, pos)

    def __repr__(self):
        return "%s %s"%(self.name,self.next)

    def __hash__(self):
        return hash(self.name)*hash(self.next)

class Reduce(Rule):
    def __init__(self, name, p):
        self.name=name
        self.p=p

    def __repr__(self):
        return "-> %s[%d] "%(self.name,self.p)

    def __hash__(self):
        return hash(self.name)*hash(self.next)*p

    def process(self, parser, item, pos):
        parser.reduce(self.name, item.start, pos)

class Precedence(object):
    def __init__(self, name, operator, precedence, next):
        self.name=name
        self.next=next
        self.operator = operator
        self.precedence = precedence

    def __repr__(self):
        return "%s%s%d %s"%(self.name,self.operator.__name__,self.precedence, self.next)
    def __hash__(self):
        return hash((self.name, self.rules))

class Disjunction(Rule):
    def __init__(self, rules):
        self.rules = rules

    def __repr__(self):
        return "(%s)"%(" | ".join(str(r) for r in self.rules))

    def __hash__(self):
        return hash(self.rules)

    def process(self, parser, item, pos):
        for rule in self.rules:
            rule.process(parser,item, pos)

    def __repr__(self):
        return  str(self.rules)

g = Grammar()

g.A = (g.A + "a") 
g.A = ("a" + g.A) 
g.A = "a" | g.B
g.B = "b"

print "predict", g._rules.predict("A")

print

p = g.A.parser()

print 'parser',  p

p.feed("a")

print
print 'fed a', p
 
p.feed("a")

print
print 'fed a',p

p.feed("a")

print
print 'fed a',p


print 'recognized', p.parsed()


p = g.A.parser()
p.feed("aba")

print p

import unittest2
import slayer



class GrammarTest(unittest2.TestCase):
    def testCase(self):
        g = slayer.Grammar()

        g.A = (g.A + "a") 
        g.A = ("a" + g.A) 
        g.A = "a" | g.B
        g.B = "b"
        self.assertEqual(3, len( g._rules.predict("A")))

        p = g.A.parser()
        print p
        print
        p.feed("a")
        print p
        print
        p.feed("a")
        p.feed("a")

        self.assertTrue(p.parsed())

        p = g.A.parser()
        p.feed("aba")
        self.assertTrue(p.parsed())



class ExprTest(unittest2.TestCase):
    def testCase(self):
        g = slayer.Grammar()

        g.add = (g.expr < 20) + "+" + (g.expr <= 20)
        g.sub = (g.expr < 20) + "-" + (g.expr <= 20)
        g.mul = (g.expr <= 10) + "*" + (g.expr < 10)
        g.div = (g.expr <= 10) + "/" + (g.expr < 10)

        def op_build(a,b,c): 
            return (b, a,c)

        g.subexpr = "(" + (g.expr <= 100) + ")"
        def sub_build(a,b,c): 
            return b

        g.number = slayer.lift("0") | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"

        g.expr[0] = g.subexpr | g.number 
        g.expr[20] = g.add | g.sub 
        g.expr[10] = g.mul | g.div


        p = g.expr.parser()
        print p
        p.feed("1*2+3*4")

        print p
        self.assertTrue(p.parsed())

if __name__ == '__main__':
    unittest2.main()

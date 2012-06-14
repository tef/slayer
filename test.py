import unittest2
import slayer



class EncodingTest(unittest2.TestCase):
    def testCase(self):
        g = slayer.Grammar()

        g.A = (g.A + "a") 
        g.A = ("a" + g.A) 
        g.A = "a" | g.B
        g.B = "b"
        self.assertEqual(3, len( g._rules.predict("A")))

        p = g.A.parser()
        p.feed("a")
        p.feed("a")
        p.feed("a")

        self.assertTrue(p.parsed())

        p = g.A.parser()
        p.feed("aba")
        self.assertTrue(p.parsed())

if __name__ == '__main__':
    unittest2.main()

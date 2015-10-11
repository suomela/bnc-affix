import collections
import itertools
import os
import re

HEAD = [
    'Headword',         # 0
    'BNC PoS',          # 1
    'Confirmed PoS',    # 2
    'Tokens',           # 3
    'Summed',           # 4
    'Comment',          # 5
    'Types'             # 6
]

SECTIONS = ['MAIN', 'CONVERSIONS', 'NAMES']
SECTIONS_DUP = SECTIONS + ['DUPLICATES']

DUP_RE = re.compile(r"duplicate of +'([^']+)'(?:\Z|; )")

def fix_plural(x):
    if x.endswith('RS'):
        return x[:-1]
    else:
        assert False, x

def fix_token(t):
    a, b = t.word, t.goodpos
    if b == '(NN2)':
        return fix_plural(a), '(NN1/2)'
    return a, b

def simplify_pos(x):
    if x == '(NN1/2)':
        return '(NN1)'
    else:
        return x

def toint(s):
    return int(s.replace(',', ''))

def parse_duplicate(s):
    m = DUP_RE.match(s)
    assert m is not None, s
    return m.group(1)

def extract(a):
    return [
        'NP0' in a.goodpos,
        a.goodpos.startswith('(V'),
    ]

def compatible(a, b):
    return extract(a) == extract(b)


Token = collections.namedtuple('Token',
    ['word', 'bncpos', 'goodpos', 'tokens', 'summed']
)


class Word:
    def __init__(self, word):
        self.word = word
        self.sect = { s: [] for s in SECTIONS }
        self.dup = []

    def tell(self, current, token):
        assert token.word == self.word
        self.sect[current].append(token)

    def tell_dup(self, token):
        self.dup.append(token)

    def resolve_dups(self):
        m_total = 0
        missing = []
        for section in SECTIONS:
            for token in self.sect[section]:
                m = token.summed - token.tokens
                if m > 0:
                    missing.append((m, section, token))
                    m_total += m
        d_total = 0
        for token in self.dup:
            d_total += token.tokens
        assert d_total == m_total, self.word
        assert len(missing) <= len(self.dup), self.word
        result = self.try_match([], missing, self.dup, False)
        assert len(result) > 0, self.word
        if len(result) > 1:
            result = self.try_match([], missing, self.dup, True)
        assert len(result) == 1
        self.dup_mapping = result[0]
        assert len(self.dup_mapping) == len(self.dup)

    def try_match(self, mapping, missing, dups, heuristic):
        if len(dups) == 0:
            return [mapping]
        good = []
        for i in range(len(missing)):
            r = self.try_match_one(mapping, i, missing, dups, heuristic)
            if len(r) == 0:
                pass
            elif len(r) == 1:
                good += r
            else:
                return r
            if len(good) > 1:
                return good
        assert len(good) <= 1
        return good

    def try_match_one(self, mapping, i, missing, dups, heuristic):
        m, section, m_token = missing[i]
        d_token = dups[0]
        dups2 = dups[1:]
        mapping2 = mapping + [(m_token, section)]
        if heuristic:
            if not compatible(m_token, d_token):
                return []
        left = m - d_token.tokens
        if left == 0:
            missing2 = missing[:i] + missing[i+1:]
            return self.try_match(mapping2, missing2, dups2, heuristic)
        elif left > 0:
            new = [(left, section, m_token)]
            missing2 = missing[:i] + new + missing[i+1:]
            return self.try_match(mapping2, missing2, dups2, heuristic)
        else:
            return []


class Parser:
    def __init__(self, builder, suffix, filenum, f_label, typos):
        self.builder = builder
        self.words = {}
        self.suffix = suffix
        self.filenum = filenum
        self.c_label = '{}'.format(suffix)
        self.f_label = f_label
        self.typos = typos
        if filenum is None:
            self.infile = 'input/morphoquantics/_{}.txt'.format(suffix)
            self.header = '-{} '.format(suffix)
        else:
            self.infile = 'input/morphoquantics/_{}_sup{}.txt'.format(suffix, filenum)
            self.header = '-{}{} '.format(suffix, filenum)

    def get_word(self, word):
        if word not in self.words:
            self.words[word] = Word(word)
        return self.words[word]

    def read_input(self):
        with open(self.infile) as f:
            l = f.readline()
            assert l.startswith(self.header), l
            l = f.readline().rstrip('\n')
            assert l == '', l
            l = f.readline().rstrip('\n')
            fields = l.split('\t')
            assert fields == HEAD, l
            current = 'MAIN'
            for l in f:
                l = l.rstrip('\n')
                if l == '':
                    continue
                fields = l.split('\t')
                assert len(fields) == len(HEAD), l
                empties = [x == '' for x in fields]
                if all(empties):
                    pass
                elif all(empties[1:]):
                    assert fields[0] in SECTIONS_DUP
                    current = fields[0]
                elif fields[0] == 'TOTALS':
                    pass
                else:
                    assert not any(empties[:5]), l
                    token = Token(
                        word=fields[0],
                        bncpos=fields[1],
                        goodpos=fields[2],
                        tokens=toint(fields[3]),
                        summed=toint(fields[4]),
                    )
                    comment = fields[5]
                    types = fields[6]
                    if current == 'DUPLICATES':
                        origword = parse_duplicate(comment).upper()
                        if origword in self.typos:
                            origword = self.typos[origword]
                        assert origword in self.words, origword
                        assert token.summed == 0 or token.summed == token.tokens
                        self.words[origword].tell_dup(token)
                    else:
                        assert types == '1', types
                        assert token.summed >= token.tokens
                        assert token.summed > 0
                        w = self.get_word(token.word)
                        w.tell(current, token)

    def build_wordlist(self):
        self.wordlist = [ w for word, w in sorted(self.words.items()) ]

    def resolve_dups(self):
        for w in self.wordlist:
            w.resolve_dups()

    def add_map(self, token, section, lemma):
        if token.tokens == 0:
            return
        assert token.bncpos != '-'
        key = (token.word, token.bncpos)
        word, pos = fix_token(lemma)
        pos = simplify_pos(pos)
        f_value = (self.f_label, section, word, pos)
        c_value = (self.c_label, section, word, pos)
        self.builder.f_map[key][f_value] += token.tokens
        self.builder.c_map[key][c_value] += token.tokens
        self.builder.count[(word, pos)] += token.tokens

    def build_map(self):
        for w in self.wordlist:
            for section in SECTIONS:
                for token in w.sect[section]:
                    assert token.word == w.word
                    self.add_map(token, section, token)
            for i in range(len(w.dup)):
                d_token = w.dup[i]
                m_token, section = w.dup_mapping[i]
                assert m_token.word == w.word
                self.add_map(d_token, section, m_token)



class Builder:
    def __init__(self):
        self.c_map = collections.defaultdict(collections.Counter)
        self.f_map = collections.defaultdict(collections.Counter)
        self.count = collections.Counter()
        self.parsers = []
        self.plural_map = {}

    def read_one(self, suffix, filenum, f_label, typos):
        parser = Parser(self, suffix, filenum, f_label, typos)
        print(parser.infile)
        parser.read_input()
        self.parsers.append(parser)

    def process(self):
        for parser in self.parsers:
            parser.build_wordlist()
            parser.resolve_dups()
            parser.build_map()

    def report(self):
        for vmap, version in [
            (self.c_map, 'coarse'),
            (self.f_map, 'fine')
        ]:
            outfile = 'output/morphoquantics/{}-map.txt'.format(version)
            dupfile = 'output/morphoquantics/{}-ambiguous.txt'.format(version)
            hapfile = 'output/morphoquantics/{}-hapax.txt'.format(version)
            print(outfile)
            print(dupfile)
            print(hapfile)
            f = open(outfile, 'w')
            fdup = open(dupfile, 'w')
            fhap = open(hapfile, 'w')
            for key in sorted(vmap.keys()):
                values = sorted(vmap[key].most_common())
                for value, count in values:
                    row = key + value + (count,)
                    tsv = '\t'.join(str(x) for x in row)
                    print(tsv, file=f)
                    if len(values) > 1:
                        print(tsv, file=fdup)
                    label, section, word, pos = value
                    if self.count[(word, pos)] == 1:
                        print(tsv, file=fhap)
            f.close()
            fdup.close()
            fhap.close()


def process(suffixes, typos):
    builder = Builder()
    os.makedirs('output/morphoquantics', exist_ok=True)
    for suffix, filenum, f_label in suffixes:
        builder.read_one(suffix, filenum, f_label, typos)
    builder.process()
    builder.report()

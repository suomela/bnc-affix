import collections
import itertools
import os
import bnc_fields

IDIR = 'input-bnc'
MDIR = 'output-morphoquantics'
ODIR = 'output-bnc'

def tprint(f, l):
    f.write('\t'.join(str(x) for x in l))
    f.write('\n')

def countersort(c):
    return sorted(c.most_common(), key=lambda x: (-x[1], x[0]))

def process(suffixes, labels, sections=['MAIN'], mapfile='coarse-map.txt', prefix=None, missfiles=False):
    def ofn(x):
        if prefix is not None:
            return os.path.join(ODIR, prefix + '-' + x)
        else:
            return os.path.join(ODIR, x)
    mapfile = os.path.join(MDIR, mapfile)
    matchfile = ofn('match.txt')
    badfile = ofn('bad.txt')
    outfile = ofn('relevant.txt')
    os.makedirs(ODIR, exist_ok=True)
    word_pos_map = collections.defaultdict(list)
    word_pos_expected = collections.Counter()
    word_pos_got = collections.Counter()
    word_pos_set = set()
    print(mapfile)
    totalcount = 0
    with open(mapfile) as f:
        for l in f:
            fields = l.rstrip('\n').split('\t')
            word, pos, label, section, lemma, goodpos, count = fields
            if label not in labels:
                continue
            if section not in sections:
                continue
            count = int(count)
            key = (word, pos)
            totalcount += count
            word_pos_expected[key] += count
            word_pos_set.add(key)
            word_pos_map[key].append((label, section, lemma, goodpos))

    relevant_hits = []
    for suffix in suffixes:
        this_word_pos_miss = collections.Counter()
        this_word_miss = collections.Counter()
        this_word_hit = collections.Counter()
        this_pos_miss = collections.Counter()
        this_pos_hit = collections.Counter()
        hitfile = os.path.join(IDIR, '{}.txt'.format(suffix))
        print(hitfile)
        with open(hitfile, encoding="latin1") as f:
            l = f.readline()
            header = l.rstrip('\n\t').split('\t')
            assert header == bnc_fields.fields
            for l in f:
                fields = l.rstrip('\n').split('\t')
                word_pos = fields[bnc_fields.i_word_pos]
                texttype = fields[bnc_fields.i_texttype]
                word, pos = word_pos.split('_')
                word = word.upper()
                pos = '({})'.format(pos)
                key = (word, pos)
                if key in word_pos_set:
                    word_pos_got[key] += 1
                    this_word_hit[word] += 1
                    this_pos_hit[pos] += 1
                else:
                    this_word_pos_miss[key] += 1
                    this_word_miss[word] += 1
                    this_pos_miss[pos] += 1
                if texttype == 'Demographically sampled':
                    relevant_hits.append((word, pos, fields))
        if missfiles:
            missfile = ofn('miss-word-{}.txt'.format(suffix))
            print(missfile)
            with open(missfile, 'w') as f:
                for word, count in countersort(this_word_miss):
                    tprint(f, (word, count, this_word_hit[word]))
            missfile = ofn('miss-pos-{}.txt'.format(suffix))
            print(missfile)
            with open(missfile, 'w') as f:
                for pos, count in countersort(this_pos_miss):
                    tprint(f, (pos, count, this_pos_hit[pos]))
            missfile = ofn('miss-wordpos-{}.txt'.format(suffix))
            print(missfile)
            with open(missfile, 'w') as f:
                for key, count in countersort(this_word_pos_miss):
                    word, pos = key
                    tprint(f, (word, pos, count))

    goodcount = 0
    word_pos_good = set()
    print(matchfile)
    print(badfile)
    f = open(matchfile, 'w')
    fbad = open(badfile, 'w')
    for key in sorted(word_pos_set):
        expected = word_pos_expected[key]
        got = word_pos_got[key]
        diff = got - expected
        if diff > 0:
            sym = '+' * diff
        else:
            sym = '-' * (-diff)
        row = key + (expected, got, sym)
        tsv = '\t'.join(str(x) for x in row)
        print(tsv, file=f)
        absdiff = abs(diff)
        if expected < 10:
            isbad = absdiff > 0
        elif expected < 100:
            isbad = absdiff > 1
        else:
            isbad = absdiff > 2
        if len(word_pos_map[key]) != 1:
            isbad = True
        if isbad:
            print(tsv, file=fbad)
        if not isbad:
            goodcount += got
            word_pos_good.add(key)
    f.close()
    fbad.close()

    print(outfile)
    relevantcount = 0
    with open(outfile, 'w') as f:
        for word, pos, fields in relevant_hits:
            key = (word, pos)
            if key not in word_pos_good:
                continue
            label, section, lemma, goodpos = word_pos_map[key][0]
            row = [word, pos, label, section, lemma, goodpos] + fields
            tsv = '\t'.join(str(x) for x in row)
            print(tsv, file=f)
            relevantcount += 1

    print('expected: {}'.format(totalcount))
    print('good: {}'.format(goodcount))
    print('candidate: {}'.format(len(relevant_hits)))
    print('relevant: {}'.format(relevantcount))

threshold = 2
leave_out = 3

class Stat:
    def __init__(self):
        self.cat_text = collections.defaultdict(collections.Counter)

    def feed(self, text, speaker, cat):
        self.cat_text[cat][text] += 1

    def calc_cat(self, cat):
        mc = [ c for v, c in self.cat_text[cat].most_common() ]
        return sum(mc), sum(mc[leave_out:])

    def calc(self, cats, lemma, result):
        r = []
        for cat in cats:
            r.append(self.calc_cat(cat))
        n = len(cats)
        for i in range(n):
            diff = min([ r[i][1] - r[j][0] for j in range(n) if i != j ])
            if diff >= threshold:
                row = (lemma, cats[i], diff) + tuple(x for s in r for x in s)
                result.append(row)

def find_overuse():
    sexes = ['Female', 'Male']
    sc_groups = [['AB', 'C1'], ['C2', 'DE']]
    scs = ['+'.join(x) for x in sc_groups]
    sex_scs = [' '.join(x) for x in itertools.product(sexes, scs)]
    stat_sex = collections.defaultdict(Stat)
    stat_sc = collections.defaultdict(Stat)
    stat_sex_sc = collections.defaultdict(Stat)
    with open(os.path.join(ODIR, 'relevant.txt')) as f:
        for l in f:
            fields = l.rstrip('\n').split('\t')
            word, pos, label, section, lemma, goodpos = fields[:6]
            rest = fields[6:]
            text = rest[bnc_fields.i_text]
            social_class = rest[bnc_fields.i_social_class]
            sex = rest[bnc_fields.i_sex]
            speaker = rest[bnc_fields.i_speaker]
            stat_sex[lemma].feed(text, speaker, sex)
            for sc_group in sc_groups:
                if social_class in sc_group:
                    sc = '+'.join(sc_group)
                    stat_sc[lemma].feed(text, speaker, sc)
                    stat_sex_sc[lemma].feed(text, speaker, sex + ' ' + sc)
    with open(os.path.join(ODIR, 'overuse.txt'), 'w') as f:
        for stat, cats in [(stat_sex, sexes), (stat_sc, scs), (stat_sex_sc, sex_scs)]:
            head = ["lemma", "category", "excess"]
            for cat in cats:
                head.append(cat)
                head.append('')
            tprint(f, head)
            result = []
            for lemma in sorted(stat.keys()):
                stat[lemma].calc(cats, lemma, result)
            result = sorted(result, key=lambda x: (x[1], -x[2]))
            for r in result:
                tprint(f, r)
            tprint(f, ())

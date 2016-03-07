import collections
import itertools
import os
import sys
import xlrd
import bnc_fields

IDIR = 'input/bnc'
MDIR = 'output/morphoquantics'
ODIR = 'output/bnc'
MAIN = 'MAIN'

def tprint(f, l):
    f.write('\t'.join(str(x) for x in l))
    f.write('\n')

def countersort(c):
    return sorted(c.most_common(), key=lambda x: (-x[1], x[0]))

def fix_str(v):
    if type(v) is float:
        return str(int(v))
    else:
        print(type(v))
        assert type(v) is str
        return v

def fix_int(v):
    if type(v) is float:
        return int(v)
    else:
        assert type(v) is int
        return v

def get_bnc_word_pos(word_pos):
        word, pos = word_pos.split('_')
        word = word.upper()
        pos = '({})'.format(pos)
        return word, pos

class Entry:
    def __init__(self, lemma, pos, label):
        self.lemma = lemma
        self.pos = pos
        self.label = label

class SkipEntry:
    pass

def get_corrections(word_pos_map, correction_label_map, correction_default_pos):
    corrections = {}
    cdir = os.path.join(IDIR, 'corrections')
    for filename in sorted(os.listdir(cdir)):
        if filename.startswith('~'):
            continue
        if filename.endswith('.xlsx'):
            cpath = os.path.join(cdir, filename)
            print(filename)
            book = xlrd.open_workbook(cpath)
            sheet = book.sheet_by_index(0)
            header = [ x.value for x in sheet.row(0) ]
            index = {}
            for c, f in enumerate(header):
                index[f] = c
            c_text = index['Textname']
            c_sunit = index['S-unit number']
            c_where = index['Matchbegin corpus position']
            c_word_pos = index['Tagged Query item']
            c_lemma = index['Lemma']
            c_kind = index.get('Kind', None)
            for r in range(1, sheet.nrows):
                text = sheet.cell(r, c_text).value
                sunit = fix_str(sheet.cell(r, c_sunit).value)
                where = fix_int(sheet.cell(r, c_where).value)
                lemma = sheet.cell(r, c_lemma).value
                if lemma == '':
                    e = SkipEntry()
                else:
                    if c_kind is None:
                        word, pos = get_bnc_word_pos(sheet.cell(r, c_word_pos).value)
                        mq = word_pos_map[(word, pos)]
                        assert len(mq) == 1
                        label = mq[0][0]
                    else:
                        label = sheet.cell(r, c_kind).value
                        if correction_label_map is not None:
                            label = correction_label_map[label]
                    assert correction_default_pos is not None
                    e = Entry(lemma.upper(), correction_default_pos, label)
                key = (text, sunit, where)
                e.seen = False
                assert key not in corrections
                corrections[key] = e
    return corrections

def process(suffixes, labels, mapfile='coarse-map.txt', prefix=None, expect_fewer=[], correction_label_map=None, correction_default_pos=None):

    # Output file names

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

    # Read Morphoquantics mappings

    word_pos_map = collections.defaultdict(list)
    word_pos_expected = collections.Counter()
    word_pos_set = set()
    print(mapfile)
    totalcount = 0
    with open(mapfile) as f:
        for l in f:
            fields = l.rstrip('\n').split('\t')
            word, pos, label, section, lemma, goodpos, count = fields
            if label not in labels:
                continue
            if section != MAIN:
                continue
            count = int(count)
            key = (word, pos)
            totalcount += count
            word_pos_expected[key] += count
            word_pos_set.add(key)
            word_pos_map[key].append((label, section, lemma, goodpos))

    # Read BNC

    word_pos_got = collections.Counter()
    relevant_hits = []
    for suffix in suffixes:
        hitfile = os.path.join(IDIR, '{}.txt'.format(suffix))
        print(hitfile)
        with open(hitfile, encoding="latin1") as f:
            l = f.readline()
            header = l.rstrip('\n\t').split('\t')
            assert header == bnc_fields.fields
            for l in f:
                fields = l.rstrip('\n').split('\t')
                texttype = fields[bnc_fields.i_texttype]
                word, pos = get_bnc_word_pos(fields[bnc_fields.i_word_pos])
                key = (word, pos)
                if key in word_pos_set:
                    word_pos_got[key] += 1
                if texttype == 'Demographically sampled':
                    relevant_hits.append((word, pos, fields))

    # Compare Morphoquantics and BNC

    expect_fewer = set(expect_fewer)
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
        if key in expect_fewer:
            assert diff < 0
            isbad = False
        elif expected < 10:
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

    # Read manual corrections

    corrections = get_corrections(word_pos_map, correction_label_map, correction_default_pos)

    # Write output

    print(outfile)
    relevantcount = 0
    with open(outfile, 'w') as f:
        for word, pos, fields in relevant_hits:
            text = fields[bnc_fields.i_text]
            sunit = fields[bnc_fields.i_sunit]
            where = int(fields[bnc_fields.i_where])
            key1 = (text, sunit, where)
            key2 = (word, pos)
            if key1 in corrections:
                e = corrections[key1]
                assert not e.seen
                e.seen = True
                if isinstance(e, SkipEntry):
                    continue
                row = [word, pos, e.label, MAIN, e.lemma, e.pos] + fields
            elif key2 in word_pos_good:
                label, section, lemma, goodpos = word_pos_map[key2][0]
                row = [word, pos, label, section, lemma, goodpos] + fields
            else:
                assert key2 not in word_pos_set
                continue
            tsv = '\t'.join(str(x) for x in row)
            print(tsv, file=f)
            relevantcount += 1

    for key, e in corrections.items():
        assert e.seen

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

import collections
import os
import shutil
import sqlite3
import bnc_fields

templatefile = '../../types/template/types.sqlite'
metadatadb = '../../bnc-metadata-output/bnc.db'

ODIR = 'output/bnc'
DBDIR = 'output/db'

BAD_URL = 'http://new-bncweb.lancs.ac.uk/'
GOOD_URL = 'http://bncweb.lancs.ac.uk/'
SPEAKER_URL = 'http://bncweb.lancs.ac.uk/cgi-binbncXML/speakerInfo_new.pl?text={}&spid={}&urlTest=yes'

class Dataset:
    def __init__(self):
        self.tokenlist = collections.defaultdict(list)
        self.tokeninfo = {}

def create(prefixes=[None], label_map=lambda x: x, setting_filter=None, existing=False):
    groups = ('gender', 'social class', 'social class + gender', 'age', 'age + gender')
    sex_map = { 'f': 'Female', 'm': 'Male' }
    age_descr_map = {
        'Ag0':   '-14', 'Ag1': '15-24', 'Ag2': '25-34',
        'Ag3': '35-44', 'Ag4': '45-59', 'Ag5': '60-',
        'X': '?'
    }
    age_group_map = {
        'Ag0': '-24', 'Ag1': '-24', 'Ag2': '25-44',
        'Ag3': '25-44', 'Ag4': '45-', 'Ag5': '45-',
        'X': None
    }
    sc_groups = [['AB', 'C1'], ['C2', 'DE']]

    conn = sqlite3.connect(metadatadb)

    settings = set()
    for text, setting, l, a in conn.execute('''
        SELECT fileid, settingid, LOWER(locale), LOWER(activity) FROM bnc_setting
    '''):
        if setting_filter is None:
            ok = True
        elif setting_filter == 'home':
            if l in ('home', 'at home', 'bedroom', 'home, bedroom', 'kitchen', 'lounge', 'mome'):
                ok = True
            elif l == 'sitting at table' and a == 'having breakfast':
                ok = True
            else:
                ok = False
        else:
            assert False
        if ok:
            settings.add((text, setting))

    relevant_wc = collections.Counter()
    relevant_line = {}
    for text, sunit, speaker, setting, wc in conn.execute('''
        SELECT fileid, n, personid, settingid, wordcount FROM bnc_s
    '''):
        if (text, setting) in settings:
            relevant_wc[(text, speaker)] += wc
            relevant_line[(text, sunit)] = True
        else:
            relevant_line[(text, sunit)] = False

    speaker_wc = {}
    speaker_descr = {}
    speaker_link = {}
    colls = { group: collections.defaultdict(set) for group in groups }
    for text, speaker, agegroup, sex, sc, occupation in conn.execute('''
        SELECT fileid, personid, ageGroup, sex, soc, occupation FROM bnc_person
    '''):
        if relevant_wc[(text, speaker)] == 0:
            continue
        if sex is None or sex == 'u':
            continue
        if sc is None or sc == 'UU':
            continue
        colls['gender'][sex_map[sex]].add(speaker)
        for sc_group in sc_groups:
            if sc in sc_group:
                groupcode = '+'.join(sc_group)
                colls['social class'][groupcode].add(speaker)
                groupcode += ' ' + sex_map[sex]
                colls['social class + gender'][groupcode].add(speaker)
        groupcode = age_group_map[agegroup]
        if groupcode is not None:
            colls['age'][groupcode].add(speaker)
            groupcode += ' ' + sex_map[sex]
            colls['age + gender'][groupcode].add(speaker)
        descr = [sc, sex, age_descr_map[agegroup]]
        if occupation is not None:
            descr.append(occupation)

        assert speaker not in speaker_wc
        speaker_wc[speaker] = relevant_wc[(text, speaker)]
        speaker_descr[speaker] = ' '.join(descr)
        speaker_link[speaker] = SPEAKER_URL.format(text, speaker)

    conn.close()

    datasets = collections.defaultdict(Dataset)
    lemma_map = {}
    for prefix in prefixes:
        if prefix is not None:
            filename = os.path.join(ODIR, prefix + '-relevant.txt')
        else:
            filename = os.path.join(ODIR, 'relevant.txt')
        with open(filename) as f:
            for l in f:
                fields = l.rstrip('\n').split('\t')
                word, pos, label, section, lemma, goodpos = fields[:6]
                rest = fields[6:]
                text = rest[bnc_fields.i_text]
                sunit = rest[bnc_fields.i_sunit]
                speaker = rest[bnc_fields.i_speaker]
                if not relevant_line[(text, sunit)]:
                    continue
                if speaker not in speaker_wc:
                    continue
                if lemma in lemma_map:
                    assert lemma_map[lemma] == (section, goodpos)
                else:
                    lemma_map[lemma] = (section, goodpos)
                token = lemma.lower()
                sex = rest[bnc_fields.i_sex]
                assert speaker in colls['gender'][sex]
                left = rest[bnc_fields.i_left]
                this = rest[bnc_fields.i_this]
                right = rest[bnc_fields.i_right]
                url = rest[bnc_fields.i_url]
                if url[:len(BAD_URL)] == BAD_URL:
                    url = GOOD_URL + url[len(BAD_URL):]
                ds = datasets[label_map(label)]
                ds.tokenlist[(speaker,token)].append((left, this, right, url))

    dbfile = os.path.join(DBDIR, 'types.sqlite')
    if not existing:
        os.makedirs(DBDIR, exist_ok=True)
        shutil.copy(templatefile, dbfile)
    conn = sqlite3.connect(dbfile)
    conn.execute('''PRAGMA foreign_keys = ON''')
    corpus = 'bnc-spoken-demo'
    if setting_filter is not None:
        corpus += '-' + setting_filter
    conn.execute(
        'INSERT INTO corpus (corpuscode) VALUES (?)',
        (corpus,)
    )
    for speaker, wc in sorted(speaker_wc.items()):
        conn.execute(
            'INSERT INTO sample (corpuscode, samplecode, wordcount, description, link) VALUES (?, ?, ?, ?, ?)',
            (corpus, speaker, wc, speaker_descr[speaker], speaker_link[speaker])
        )
    for dslabel in sorted(datasets.keys()):
        ds = datasets[dslabel]
        conn.execute(
            'INSERT INTO dataset (corpuscode, datasetcode) VALUES (?, ?)',
            (corpus, dslabel)
        )
        for key in sorted(ds.tokenlist.keys()):
            speaker, token = key
            tokenlist = ds.tokenlist[key]
            conn.execute(
                'INSERT INTO token (corpuscode, samplecode, datasetcode, tokencode, tokencount) VALUES (?, ?, ?, ?, ?)',
                (corpus, speaker, dslabel, token, len(tokenlist))
            )
            for left, this, right, url in tokenlist:
                conn.execute(
                    'INSERT INTO context (corpuscode, samplecode, datasetcode, tokencode, before, word, after, link) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (corpus, speaker, dslabel, token, left, this, right, url)
                )
    for group in groups:
        for key in sorted(colls[group].keys()):
            conn.execute(
                'INSERT INTO collection (corpuscode, collectioncode, groupcode) VALUES (?, ?, ?)',
                (corpus, key, group)
            )
            for speaker in sorted(colls[group][key]):
                conn.execute(
                    'INSERT INTO sample_collection (corpuscode, samplecode, collectioncode) VALUES (?, ?, ?)',
                    (corpus, speaker, key)
                )
    conn.execute('DELETE FROM defaultstat')
    for stat in ('type-token', 'type-word', 'token-word'):
        conn.execute('INSERT INTO defaultstat VALUES (?)', (stat,))
    conn.commit()

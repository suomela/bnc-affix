bnc-affix
=========

Analysing the productivity of affixes with BNC and Morphoquantics data.


General setup
-------------

We expect that types2 can be found at `../types`. To set it up:

    cd ..
    git clone git://github.com/suomela/types.git
    cd types
    ./config
    make
    cd -

For more information, see http://users.ics.aalto.fi/suomela/types2/



Input data
----------

We will need input data from two sources:

- BNC search results: http://bncweb.lancs.ac.uk/

- Morphoquantics: http://morphoquantics.co.uk/

BNC search results are stored in the following locations:

    */input/bnc/*.txt

Morphoquantics data is stored in the following locations:

    */input/morphoquantics/*.txt

We use the following suffixes in our studies:

- er: Suffixes "-er" (noun), "-or" (noun)

- adverb: Suffixes "-ly" (adverb), "-wise" (adverb)

For these studies, BNC search results are stored in the following
locations. We follow the convention that the files are named after
the search term:

    er/input/bnc/er.txt
    er/input/bnc/or.txt
    adverb/input/bnc/ly.txt
    adverb/input/bnc/wise.txt

Morphoquantics files are stored in the following locations. We follow
the naming convention used by Morphoquantics:

    er/input/morphoquantics/_er_sup1.txt
    er/input/morphoquantics/_er_sup2.txt
    er/input/morphoquantics/_er_sup3.txt
    er/input/morphoquantics/_er_sup4.txt
    er/input/morphoquantics/_or_sup1.txt
    er/input/morphoquantics/_or_sup2.txt
    adverb/input/morphoquantics/_ly_sup2.txt
    adverb/input/morphoquantics/_wise.txt

For the BNC search results, do a search for e.g. *er in spoken texts and
download the results using the settings shown in
docs/bncweb_downloadsettings.png.

Usage
-----

Once all files are in place, you can run everything as follows:

    ./do-all.sh

To get approximate results faster, try:

    ./do-all.sh --quick

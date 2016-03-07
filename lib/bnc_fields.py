fields = [
    'Number of hit',
    'Textname',
    'S-unit number',
    'Speaker-ID (if applicable)',
    'Left context',
    'Query item',
    'Right context',
    'Tagged Left context',
    'Tagged Query item',
    'Tagged Right context',
    'Spoken or Written',
    'Text type',
    'Genre',
    'Publication date',
    'Derived text type',
    'Text Sample',
    'Medium of Text',
    'Text Domain',
    'Perceived level of difficulty',
    'Age of Author',
    'Domicile of Author',
    'Sex of Author',
    'Type of Author',
    'Age of Audience',
    'Target audience sex',
    'Estimated circulation size',
    'Type of Interaction',
    'Region where spoken text was captured',
    'Age of Respondent',
    'Gender of Respondent',
    'Social Class of Respondent',
    'Domain (spoken context governed texts)',
    'Age',
    'Sex',
    'Social Class',
    'First Language',
    'Education',
    'Dialect/Accent',
    'URL',
    'Matchbegin corpus position',
    'Matchend corpus position',
]

index = {}
for i, f in enumerate(fields):
    index[f] = i

i_text = index['Textname']
i_sunit = index['S-unit number']
i_word_pos = index['Tagged Query item']
i_texttype = index['Text type']
i_speaker = index['Speaker-ID (if applicable)']
i_sex = index['Sex']
i_social_class = index['Social Class']
i_left = index['Left context']
i_this = index['Query item']
i_right = index['Right context']
i_url = index['URL']
i_where = index['Matchend corpus position']

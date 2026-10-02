"""Bounded musical operations over explicit input, not recognition or expert claims.

Uses the existing pitch/scale primitives and provenance contracts. Every result
retains the supplied context, source identity and the limits of its calculation.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from fractions import Fraction
from .context import LearnerContext
from .mini_exam import _pitch, LETTERS, NATURAL

REFERENCE_SOURCES = {
    'interval': 'https://musictheory.pugetsound.edu/mt21c/IntervalsIntroduction.html',
    'scale': 'https://musictheory.pugetsound.edu/mt21c/MinorScales.html',
    'chord': 'https://musictheory.pugetsound.edu/mt21c/SeventhChordsIntroduction.html',
    'solfege': 'https://viva.pressbooks.pub/openmusictheory/chapter/major-scales/',
    'meter': 'https://musictheory.pugetsound.edu/mt21c/meter.html',
    'voice_leading': 'https://musictheory.pugetsound.edu/mt21c/ObjectionableParallels.html',
}
MODES = {'major': (0,2,4,5,7,9,11,12), 'natural_minor': (0,2,3,5,7,8,10,12),
         'harmonic_minor': (0,2,3,5,7,8,11,12), 'melodic_minor': (0,2,3,5,7,9,11,12)}
CHORDS = {
    (0,4,7): ('major_triad', (0,2,4)), (0,3,7): ('minor_triad', (0,2,4)),
    (0,3,6): ('diminished_triad', (0,2,4)), (0,4,8): ('augmented_triad', (0,2,4)),
    (0,4,7,10): ('dominant_seventh', (0,2,4,6)),
    (0,4,7,11): ('major_seventh', (0,2,4,6)), (0,3,7,10): ('minor_seventh', (0,2,4,6)),
    (0,3,6,10): ('half_diminished_seventh', (0,2,4,6)),
    (0,3,6,9): ('diminished_seventh', (0,2,4,6)), (0,3,7,11): ('minor_major_seventh', (0,2,4,6)),
}


def pitch(name: str):
    if not isinstance(name,str) or not re.fullmatch(r'[A-G](?:#{1,2}|b{1,2})?[0-8]',name):
        raise ValueError('An explicit written pitch with octave and at most a double accidental is required')
    result=_pitch(name)
    if not 0 <= result[3] <= 127:
        raise ValueError('Pitch is outside the supported MIDI range')
    return result


def interval(first: str, second: str) -> dict:
    a,b=pitch(first),pitch(second)
    diatonic=(b[2]-a[2])*7 + LETTERS.index(b[0])-LETTERS.index(a[0])
    chromatic=b[3]-a[3]
    # Staff ordering and sounding direction can disagree under unusual spelling.
    direction='ascending' if diatonic>0 or (diatonic==0 and chromatic>0) else 'descending' if diatonic<0 or chromatic<0 else 'unison'
    sign=1 if diatonic>=0 else -1
    distance=chromatic*sign
    number=abs(diatonic)+1; simple=(number-1)%7+1; octaves=(number-1)//7
    base=(0,2,4,5,7,9,11)[simple-1] + 12*octaves
    difference=distance-base
    perfect=simple in (1,4,5)
    if difference==0: quality='perfect' if perfect else 'major'
    elif difference==-1 and not perfect: quality='minor'
    elif difference>0: quality='augmented' if difference==1 else f'{difference}-times-augmented'
    else:
        alteration=-difference if perfect else -difference-1
        quality='diminished' if alteration==1 else f'{alteration}-times-diminished'
    return {'first':first,'second':second,'number':number,'simple_number':simple,'quality':quality,
            'semitones':abs(chromatic),'direction':direction,'written_spelling_preserved':True,
            'enharmonic_unison':chromatic==0 and first!=second}


def scale(tonic: str, mode: str, direction: str='ascending') -> dict:
    root=pitch(tonic)
    if mode not in MODES or direction not in {'ascending','descending'}:
        raise ValueError('Supported modes are major and the three named minor forms; direction is required')
    offsets=MODES['natural_minor'] if mode=='melodic_minor' and direction=='descending' else MODES[mode]
    start=LETTERS.index(root[0]);notes=[]
    for index,semitones in enumerate(offsets):
        letter=LETTERS[(start+index)%7];octave=root[2]+(start+index)//7
        alteration=root[3]+semitones-(12*(octave+1)+NATURAL[letter])
        if abs(alteration)>2:raise ValueError('This spelling exceeds the double-accidental scope')
        name=letter+('#'*alteration if alteration>0 else 'b'*(-alteration))+str(octave)
        pitch(name);notes.append(name)
    if direction=='descending':notes.reverse()
    return {'tonic':tonic,'mode':mode,'direction':direction,'notes':notes,
            'register_convention':'tonic_argument_is_lower_endpoint_of_the_one_octave_range',
            'convention':'classical_melodic_minor_descends_as_natural_minor' if mode=='melodic_minor' else 'named_scale_pattern'}


def chord(notes: list[str]) -> dict:
    if not isinstance(notes,(list,tuple)) or not 3<=len(notes)<=12:
        raise ValueError('Provide 3–12 explicitly written chord pitches')
    pitches=[pitch(n) for n in notes];pcs={p[3]%12 for p in pitches};candidates=[]
    for name,root in zip(notes,pitches):
        spelling=name[:-1]
        if any(c['root']==spelling for c in candidates):continue
        distances=tuple(sorted((pc-root[3])%12 for pc in pcs))
        template=CHORDS.get(distances)
        if not template:continue
        letters={(LETTERS.index(p[0])-LETTERS.index(root[0]))%7 for p in pitches}
        if letters!=set(template[1]):continue
        bass=min(pitches,key=lambda p:p[3]);bass_member=(bass[3]-root[3])%12
        inversion=distances.index(bass_member)
        figures=('','6','6/4') if len(pcs)==3 else ('7','6/5','4/3','4/2')
        candidates.append({'root':spelling,'quality':template[0],'inversion':inversion,
                           'figured_bass':figures[inversion],'bass_midi':bass[3]})
    if len(candidates)!=1:
        return {'root':None,'quality':None,'candidates':candidates,'review_required':True,
                'reason':'This set is ambiguous or outside complete spelled triads/sevenths; no root or function inferred.'}
    return {**candidates[0],'notes':list(notes),'harmonic_function':'not_inferred_without_key_and_context'}


def solfege(notes, system, tonic=None, mode='major', minor_basis=None, seventh_syllable='si'):
    if not isinstance(notes,(list,tuple)) or not 1<=len(notes)<=256:
        raise ValueError('Provide a bounded explicit note sequence')
    parsed=[pitch(n) for n in notes]
    if system not in {'fixed_do','movable_do'} or seventh_syllable not in {'si','ti'}:
        raise ValueError('Select fixed_do or movable_do and the fixed-do seventh syllable convention')
    if system=='fixed_do':
        syllables=('do','re','mi','fa','sol','la',seventh_syllable)
        return {'system':system,'notes':[{'pitch':n,'syllable':syllables[LETTERS.index(p[0])],
                                          'written_accidental':p[1]} for n,p in zip(notes,parsed)],
                'convention':'fixed_letter_syllables_with_explicit_accidentals'}
    if mode not in MODES or tonic is None:
        return {'review_required':True,'notes':[],'reason':'Movable-do needs an explicit tonic and mode.'}
    root=pitch(tonic)
    if mode!='major' and minor_basis not in {'do','la'}:
        return {'review_required':True,'notes':[],'reason':'Select do-based or la-based minor before assigning syllables.'}
    expected=MODES[mode][:7]
    base=('do','re','mi','fa','sol','la','ti') if mode=='major' else ('do','re','me','fa','sol','le','te') if minor_basis=='do' else ('la','ti','do','re','mi','fa','sol')
    if mode=='harmonic_minor':base=(*base[:6],'ti' if minor_basis=='do' else 'si')
    if mode=='melodic_minor':base=(*base[:5],'la' if minor_basis=='do' else 'fi','ti' if minor_basis=='do' else 'si')
    output=[]
    for name,p in zip(notes,parsed):
        degree=(LETTERS.index(p[0])-LETTERS.index(root[0]))%7
        chroma=(p[3]-root[3])%12
        if chroma!=expected[degree]:
            return {'review_required':True,'notes':output,'reason':'Chromatic spelling is outside the selected syllable convention; specify a chromatic system.'}
        output.append({'pitch':name,'degree':degree+1,'syllable':base[degree]})
    return {'system':system,'tonic':tonic,'mode':mode,'minor_basis':minor_basis,'notes':output}


def meter(numerator, denominator, groups=None):
    if type(numerator) is not int or type(denominator) is not int or not 1<=numerator<=32 or denominator not in {1,2,4,8,16,32}:
        raise ValueError('Supported meter requires integer numerator and power-of-two denominator')
    if groups is None:
        if numerator in (6,9,12):groups=[3]*(numerator//3)
        elif numerator in (2,3,4):groups=[1]*numerator
        else:return {'review_required':True,'reason':'Irregular meter needs explicit beat grouping.'}
    if not isinstance(groups,(list,tuple)) or any(type(n) is not int or n<=0 for n in groups) or sum(groups)!=numerator:
        raise ValueError('Positive beat groups must sum to the numerator')
    return {'time_signature':f'{numerator}/{denominator}','groups':list(groups),'beats':len(groups),
            'beat_durations_quarters':[str(Fraction(n*4,denominator)) for n in groups],
            'measure_duration_quarters':str(Fraction(numerator*4,denominator)),
            'groove_or_tempo':'not_inferred_from_time_signature'}


def voice_leading(before, after, style):
    if style not in {'common_practice','jazz','pop'}:
        return {'review_required':True,'reason':'Select the style or course rule set; no universal prohibition is inferred.'}
    if not isinstance(before,dict) or not isinstance(after,dict) or set(before)!=set(after) or not 2<=len(before)<=8:
        raise ValueError('The same 2–8 named voices are required before and after')
    a={v:pitch(n) for v,n in before.items()};b={v:pitch(n) for v,n in after.items()};parallels=[]
    for left,right in itertools.combinations(before,2):
        initial=abs(a[left][3]-a[right][3]);final=abs(b[left][3]-b[right][3])
        moves=(b[left][3]-a[left][3],b[right][3]-a[right][3])
        written_before=interval(before[left],before[right]);written_after=interval(after[left],after[right])
        both_perfect=written_before['quality']==written_after['quality']=='perfect'
        perfect_fifths=both_perfect and written_before['simple_number']==written_after['simple_number']==5
        octaves=both_perfect and written_before['simple_number']==written_after['simple_number']==1 and initial>0 and final>0
        if (perfect_fifths or octaves) and moves[0]*moves[1]>0:
            parallels.append({'voices':[left,right],'interval':'perfect_fifth' if perfect_fifths else 'perfect_octave',
                              'judgment':'avoid_in_this_exercise' if style=='common_practice' else 'style_dependent_not_a_universal_error'})
    return {'style':style,'parallels':parallels,'complete_counterpoint_assessment':False,
            'checked':'similar-motion perfect fifths/octaves between the explicitly named voices',
            'not_checked':['dissonance treatment','tendency-tone resolution','species rules','phrase-level function']}


FUNCTIONS={'interval':interval,'scale':scale,'chord':chord,'solfege':solfege,'meter':meter,'voice_leading':voice_leading}
PARAMETERS={
 'interval':{'first','second'},'scale':{'tonic','mode','direction'},'chord':{'notes'},
 'solfege':{'notes','system','tonic','mode','minor_basis','seventh_syllable'},
 'meter':{'numerator','denominator','groups'},'voice_leading':{'before','after','style'}}


def evaluate(request: dict, context: LearnerContext | None=None) -> dict:
    context=context or LearnerContext()
    if not isinstance(request,dict):raise ValueError('An operation request object is required')
    operation=request.get('operation')
    if operation not in FUNCTIONS:
        return {'state':'unsupported','operation':operation,'reason':'No verified implementation for this operation.','persisted':False}
    unknown=set(request)-PARAMETERS[operation]-{'operation','source_id','passage_id'}
    if unknown:raise ValueError('Unknown operation parameters: '+', '.join(sorted(unknown)))
    source_id=request.get('source_id','explicit-user-input')
    if not isinstance(source_id,str) or not source_id or len(source_id)>240:raise ValueError('Bounded source identity required')
    inputs={k:v for k,v in request.items() if k in PARAMETERS[operation]}
    try:
        if operation=='scale' and inputs.get('mode')=='melodic_minor' and inputs.get('direction')=='descending' and any(x in context.musical_tradition.casefold() for x in ('jazz','pop')):
            data={'review_required':True,'notes':[], 'reason':'Choose the melodic-minor convention explicitly; a jazz/pop context must not silently inherit the classical descending form.'}
        else:data=FUNCTIONS[operation](**inputs)
    except TypeError as error:raise ValueError('Missing or malformed musical operation arguments') from error
    context_data={'response_language':context.response_language,'curriculum_context':dict(context.curriculum_context),
                  'terminology_preference':dict(context.terminology_preference),'analysis_framework':context.analysis_framework,
                  'musical_tradition':context.musical_tradition,'notation_and_solfege_system':dict(context.notation_and_solfege_system)}
    canonical=json.dumps({'request':request,'context':context_data},sort_keys=True,ensure_ascii=False,allow_nan=False)
    claim_id='theory:'+hashlib.sha256(canonical.encode()).hexdigest()[:24]
    state='review_required' if data.get('review_required') else 'computed_from_explicit_input'
    en={'interval':f"Count written letters for the interval number and semitones for quality: {data.get('quality')} {data.get('number')}.",
        'scale':'Spell successive scale degrees with consecutive letter names and the selected major/minor pattern.',
        'chord':'Distinguish the spelled root from the lowest note. A chord label alone does not establish harmonic function.',
        'solfege':'The explicit fixed/movable-do and minor-basis convention controls the syllables.',
        'meter':'A beat group is not necessarily one denominator note; time signature alone does not determine groove.',
        'voice_leading':'The pitch motion is a computed observation; its acceptability depends on the selected style.'}[operation]
    zh={'interval':f"先按音名字母數出音程度數，再以半音數核對性質：{data.get('quality')} {data.get('number')}。等音不代表同一種記譜音程。",
        'scale':'按連續音名字母及指定大小調形式拼寫音階；旋律小調下行採古典自然小調慣例。',
        'chord':'先辨別和弦根音，再按實際低音判定轉位；和弦名稱本身不等於和聲功能。',
        'solfege':'唱名依固定／首調及小調基準分開處理，不能只按國籍或語言推定。',
        'meter':'分組拍不一定等於拍號分母的一個音符；拍號亦不能單獨決定律動或速度。',
        'voice_leading':'音高移動是可計算的觀察，是否適合則必須按風格及課程規則判斷。'}[operation]
    explanation=zh if context.response_language=='zh-Hant' else en+' '+zh if context.response_language=='bilingual' else en
    if state=='review_required':explanation+=' '+data.get('reason','Source or specialist review remains required.')
    return {'state':state,'operation':operation,'data':data,'explanation':explanation,'source_id':source_id,
            'claim_id':claim_id,'passage_id':request.get('passage_id'),'context':context_data,
            'provenance_kind':'analytical_interpretation','official_answer':False,'musically_verified_from_scan':False,
            'reference_sources':[REFERENCE_SOURCES[operation]],'persisted':False}

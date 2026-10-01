"""A single integer sample timebase for scene, voice, music and caption events."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction as F
import math
import textwrap


@dataclass(frozen=True)
class Clock:
    sample_rate: int = 48000
    fps: int = 24

    def __post_init__(self):
        if type(self.sample_rate) is not int or type(self.fps) is not int or self.fps<=0 or self.sample_rate<=0 or self.sample_rate%self.fps:
            raise ValueError('the sample clock must represent every video frame exactly')

    @property
    def samples_per_frame(self):return self.sample_rate//self.fps
    def seconds_to_samples(self,seconds):
        value=F(seconds)*self.sample_rate
        if value<0:raise ValueError('negative time')
        return (2*value.numerator+value.denominator)//(2*value.denominator)
    def frame_ceil(self,samples):
        if type(samples) is not int or samples<0:raise ValueError('invalid sample position')
        return ((samples+self.samples_per_frame-1)//self.samples_per_frame)*self.samples_per_frame
    def frames(self,samples):
        if type(samples) is not int or samples<0 or samples%self.samples_per_frame:raise ValueError('not an exact frame boundary')
        return samples//self.samples_per_frame


@dataclass(frozen=True)
class Clip:
    asset_id: str
    role: str
    samples: int
    text: str = ''

    def __post_init__(self):
        if self.role not in {'speech','music','pause','transition','performance'}:raise ValueError('unknown audio bus')
        if type(self.samples) is not int or self.samples<=0:raise ValueError('positive final asset sample count required')
        if self.role in {'music','performance'} and not self.text.strip():raise ValueError('every music replay needs an explicit listening purpose')
        if self.role=='speech' and not self.text.strip():raise ValueError('speech requires its final text')


@dataclass(frozen=True)
class PlacedClip:
    asset_id: str
    role: str
    start: int
    end: int
    text: str = ''


@dataclass(frozen=True)
class SceneTiming:
    scene_id: str
    duration: int
    clips: tuple[PlacedClip,...]
    captions: tuple[dict,...]


def validate_windows(clips) -> None:
    for c in clips:
        if type(c.start) is not int or type(c.end) is not int or not 0<=c.start<c.end:raise ValueError('invalid audio interval')
    for music in clips:
        if music.role not in {'music','performance'}:continue
        for c in clips:
            if c is music or c.role=='pause':continue
            if max(c.start,music.start)<min(c.end,music.end):
                raise ValueError('protected musical listening window contains another audio clip')


def sequence(scene_id: str, clips, *, clock: Clock=Clock(), lead: int=12000, tail: int=24000, gap: int=12000) -> SceneTiming:
    if any(type(n) is not int or n<0 for n in (lead,tail,gap)):raise ValueError('invalid scene padding')
    cursor=lead;placed=[];captions=[]
    for clip in clips:
        # Synchronize beat starts to a frame, preserve exact final audio lengths.
        cursor=clock.frame_ceil(cursor)
        p=PlacedClip(clip.asset_id,clip.role,cursor,cursor+clip.samples,clip.text);placed.append(p)
        if clip.role=='speech':captions.append({'start':p.start,'end':p.end,'text':clip.text})
        elif clip.role in {'music','performance'}:
            captions.append({'start':p.start,'end':min(p.end,p.start+clock.sample_rate*3),'text':'[Piano — '+clip.text+']'})
        cursor=p.end+gap
    validate_windows(placed)
    return SceneTiming(scene_id,clock.frame_ceil(cursor-gap+tail),tuple(placed),tuple(captions))


def validate_reveal(question_end: int, answer_start: int, *, minimum_seconds: int=6, clock: Clock=Clock()) -> None:
    if answer_start-question_end < minimum_seconds*clock.sample_rate:raise ValueError('analytical answer revealed before listening/thinking opportunity')


def stamp(samples: int,clock: Clock=Clock(),vtt=False):
    ms=(samples*1000+clock.sample_rate//2)//clock.sample_rate
    h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02d}:{m:02d}:{s:02d}{"." if vtt else ","}{ms:03d}'


def _captions(cues,clock,vtt):
    blocks=[];previous=-1
    for i,cue in enumerate(cues,1):
        start,end=cue['start'],cue['end'];text=cue['text']
        if type(start) is not int or type(end) is not int or start<previous or end<=start or not text.strip():raise ValueError('invalid or overlapping final caption')
        if '-->' in text or '\x00' in text:raise ValueError('invalid caption text')
        previous=end
        lines=textwrap.wrap(text,width=62,break_long_words=False,break_on_hyphens=False)
        if len(lines)>2:raise ValueError('caption is too dense; split final speech into shorter phrases')
        blocks.append(f'{i}\n{stamp(start,clock,vtt)} --> {stamp(end,clock,vtt)}\n'+ '\n'.join(lines))
    return ('WEBVTT\n\n' if vtt else '')+'\n\n'.join(blocks)+'\n'


def captions_srt(cues,clock=Clock()):return _captions(cues,clock,False)
def captions_vtt(cues,clock=Clock()):return _captions(cues,clock,True)

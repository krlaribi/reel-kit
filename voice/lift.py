# Change a voice-over's pace and pitch without artefacts.
#   python lift.py in.wav out.wav <rate> <semitones>   e.g. 1.05 0.5 = 5 % faster, half a semitone up
import sys, numpy as np, soundfile as sf
from pedalboard import time_stretch
inp,out,rate,semi=sys.argv[1],sys.argv[2],float(sys.argv[3]),float(sys.argv[4])
y,sr=sf.read(inp,dtype='float32'); y=y if y.ndim==1 else y.mean(1)
z=time_stretch(y[None],sr,stretch_factor=rate,pitch_shift_in_semitones=semi,high_quality=True,transient_mode='crisp')[0]
sf.write(out,z,sr)

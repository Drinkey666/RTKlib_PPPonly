"""One explicit PC preset; no modification of native model defaults."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'config/b_verified.json'
PROFILE=json.loads(PATH.read_text(encoding='utf-8'))['environment']

def environment(parent,files=None,recovery=False):
    # No stale experimental environment can silently override this entry.
    env={k:v for k,v in parent.items() if not k.upper().startswith('RTK_PPP_')}
    env.update({'RTK_PPP_'+k:v for k,v in PROFILE.items()})
    if files:env.update({'RTK_PPP_'+k:str(v) for k,v in files.items()})
    if recovery:env['RTK_PPP_CODE_RECOVERY']='BRIDGE3'
    return env

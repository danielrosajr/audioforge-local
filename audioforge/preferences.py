"""UI language preference; kept separate from existing tutorial state."""
import json
import os
from pathlib import Path
from .tutorial import SETTINGS_FILE,CONFIG_DIR

def get_language():
    try:
        lang = json.loads(SETTINGS_FILE.read_text(encoding='utf-8')).get('language')
        return lang if lang in ('pt','en') else 'pt'
    except (OSError,ValueError,AttributeError):
        return 'pt'

def save_language(lang):
    if lang not in ('pt','en'):
        return
    CONFIG_DIR.mkdir(parents=True,exist_ok=True)
    try:
        existing=json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
        if not isinstance(existing,dict):existing={}
    except (OSError,ValueError):existing={}
    existing['language']=lang
    tmp=SETTINGS_FILE.with_name('preferences.'+str(os.getpid())+'.tmp')
    tmp.write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,SETTINGS_FILE)

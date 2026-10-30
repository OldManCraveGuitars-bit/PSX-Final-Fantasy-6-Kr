"""Native four-line field windows must reach their timed-advance controls."""
import re

TIMED_CONTROL = re.compile(r'\{(?:key|pause)\[[0-9A-Fa-f]{2}\]\}')
PAGE_BOUNDARY = re.compile(r'\{(?:key|page)\}')


def clean_field_text(normalized_text):
    """The main-dialogue builder's whitespace rules; preserve control order."""
    text='\n'.join(re.sub(' +',' ',line).strip() for line in normalized_text.splitlines())
    text=re.sub(r'\n{2,}','\n',text)
    text=re.sub(r'\n*(\{(?:page|key(?:\[[^]]+\])?)\})\n*',r'\1',text)
    return text.strip()


def timed_page_overflows(wrapped_text, rows=4):
    """Input must already use the game's 216px wrapping, not editor bounds.

    Extra lines wait for a button before later timer commands are consumed.
    Ordinary interactive dialogue can scroll and is intentionally not rejected.
    """
    result = []
    for page, text in enumerate(PAGE_BOUNDARY.split(wrapped_text), 1):
        timers = TIMED_CONTROL.findall(text)
        lines = text.count('\n') + 1
        if timers and lines > rows:
            result.append({'page': page, 'lines': lines, 'limit': rows, 'timers': timers})
    return result

# -*- coding: utf-8 -*-
"""
Fix config.py indentation errors
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
config_file = PROJECT_ROOT / "config.py"

with open(config_file, 'r', encoding='utf-8', errors='replace') as f:
 lines = f.readlines()

fixed_lines = []
i = 0
while i < len(lines):
 line = lines[i]
 
 # Fix GamePhase enum
    if 'class GamePhase(Enum):' in line:
 fixed_lines.append(line)
 i += 1
        if i < len(lines) and lines[i].strip() == '"""Current game phase - transitions dynamically based on scouting"""':
 fixed_lines.append(lines[i])
 i += 1
 # Fix enum members
        while i < len(lines) and (lines[i].strip().startswith('OPENING') or lines[i].strip().startswith('ECONOMY') or 
                                  lines[i].strip().startswith('TECH') or lines[i].strip().startswith('ATTACK') or
                                  lines[i].strip().startswith('DEFENSE') or lines[i].strip().startswith('ALL_IN')):
            fixed_lines.append('    ' + lines[i].lstrip())
 i += 1
 continue
 
 # Fix EnemyRace enum
    if 'class EnemyRace(Enum):' in line:
 fixed_lines.append(line)
 i += 1
        if i < len(lines) and '"""Opponent race"""' in lines[i]:
 fixed_lines.append(lines[i])
 i += 1
 # Fix enum members
        while i < len(lines) and (lines[i].strip().startswith('TERRAN') or lines[i].strip().startswith('PROTOSS') or 
                                  lines[i].strip().startswith('ZERG') or lines[i].strip().startswith('UNKNOWN')):
            fixed_lines.append('    ' + lines[i].lstrip())
 i += 1
 continue
 
 # Fix Config dataclass
    if '@dataclass(frozen = True)' in line or '@dataclass(frozen=True)' in line:
        fixed_lines.append('@dataclass(frozen=True)\n')
 i += 1
        if i < len(lines) and 'class Config:' in lines[i]:
 fixed_lines.append(lines[i])
 i += 1
        if i < len(lines) and '"""AI behavior configuration values (immutable)"""' in lines[i]:
 fixed_lines.append(lines[i])
 i += 1
 # Fix class attributes
        while i < len(lines) and (lines[i].strip() and not lines[i].strip().startswith('class ') and 
                                  not lines[i].strip().startswith('def ') and not lines[i].strip().startswith('@') and
                                  not lines[i].strip().startswith('#') and not lines[i].strip().startswith('REPLAY')):
 if lines[i].strip():
                fixed_lines.append('    ' + lines[i].lstrip())
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
 # Fix ConfigLoader methods
    if 'def __init__' in line and 'ConfigLoader' in ''.join(fixed_lines[-5:]):
        fixed_lines.append('    ' + line.lstrip())
 i += 1
        while i < len(lines) and (lines[i].strip().startswith('self.') or lines[i].strip() == ''):
 if lines[i].strip():
                fixed_lines.append('        ' + lines[i].lstrip())
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
    if 'def load_learned_config' in line:
        fixed_lines.append('    ' + line.lstrip())
 i += 1
        while i < len(lines) and not (lines[i].strip().startswith('def ') and 'get_config' in lines[i]):
            if lines[i].strip() and not lines[i].strip().startswith('class '):
                indent = '        ' if lines[i].strip() and not lines[i].strip().startswith('if ') else '    '
 fixed_lines.append(indent + lines[i].lstrip() if lines[i].strip() else lines[i])
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
    if 'def get_config' in line:
        fixed_lines.append('    ' + line.lstrip())
 i += 1
        while i < len(lines) and not (lines[i].strip().startswith('def ') and 'get_parameter' in lines[i]):
            if lines[i].strip() and not lines[i].strip().startswith('class '):
                indent = '        ' if lines[i].strip() and not lines[i].strip().startswith('for ') else '    '
 fixed_lines.append(indent + lines[i].lstrip() if lines[i].strip() else lines[i])
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
    if 'def get_parameter' in line:
        fixed_lines.append('    ' + line.lstrip())
 i += 1
        while i < len(lines) and not (lines[i].strip().startswith('def ') or lines[i].strip().startswith('_config_loader')):
            if lines[i].strip() and not lines[i].strip().startswith('class '):
                indent = '        ' if lines[i].strip() else '    '
 fixed_lines.append(indent + lines[i].lstrip() if lines[i].strip() else lines[i])
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
 # Fix get_config_loader
    if 'def get_config_loader' in line:
 fixed_lines.append(line)
 i += 1
        while i < len(lines) and not (lines[i].strip().startswith('def ') and 'get_learned_parameter' in lines[i]):
            if lines[i].strip() and not lines[i].strip().startswith('class '):
                fixed_lines.append('    ' + lines[i].lstrip())
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
 # Fix get_learned_parameter
    if 'def get_learned_parameter' in line:
 fixed_lines.append(line)
 i += 1
 while i < len(lines):
            if lines[i].strip() and not lines[i].strip().startswith('def ') and not lines[i].strip().startswith('class '):
                fixed_lines.append('    ' + lines[i].lstrip())
 else:
 fixed_lines.append(lines[i])
 i += 1
 break
 
 # Fix REPLAY_DIR try block
    if 'try:' in line and 'REPLAY_DIR.mkdir' in ''.join(lines[i+1:i+5]):
 fixed_lines.append(line)
 i += 1
        while i < len(lines) and ('REPLAY_DIR.mkdir' in lines[i] or 'REPLAY_SOURCE_DIR.mkdir' in lines[i] or 
                                   'REPLAY_COMPLETED_DIR.mkdir' in lines[i] or 'except Exception:' in lines[i] or
                                   'pass' in lines[i]):
            if 'REPLAY_DIR.mkdir' in lines[i] or 'REPLAY_SOURCE_DIR.mkdir' in lines[i] or 'REPLAY_COMPLETED_DIR.mkdir' in lines[i]:
                fixed_lines.append('    ' + lines[i].lstrip())
            elif 'except Exception:' in lines[i]:
 fixed_lines.append(lines[i])
            elif 'pass' in lines[i]:
                fixed_lines.append('    ' + lines[i].lstrip())
 else:
 fixed_lines.append(lines[i])
 i += 1
 continue
 
 # Fix PROTOCOL_BUFFERS_IMPL indentation
    if 'PROTOCOL_BUFFERS_IMPL' in line and line.startswith('    '):
        fixed_lines.append('    ' + line.lstrip())
 i += 1
 continue
 
 # Fix COUNTER_BUILD, THREAT_BUILDINGS indentation
    if ('COUNTER_BUILD' in line or 'THREAT_BUILDINGS' in line) and line.strip().startswith('EnemyRace') or line.strip().startswith('UnitTypeId'):
        if not line.startswith(' '):
            fixed_lines.append('    ' + line.lstrip())
 else:
 fixed_lines.append(line)
 i += 1
 continue
 
 fixed_lines.append(line)
 i += 1

with open(config_file, 'w', encoding='utf-8') as f:
 f.writelines(fixed_lines)

print("Fixed config.py indentation")
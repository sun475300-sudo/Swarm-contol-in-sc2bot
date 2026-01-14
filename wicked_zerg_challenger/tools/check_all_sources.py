#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ÀüÃ¼ ¼Ò½ºÄÚµå ÆÄÀÏ Á¡°Ë ½ºÅ©¸³Æ®
"""

import ast
import sys
from pathlib import Path
from typing import List, Dict, Tuple

def check_syntax(filepath: Path) -> Tuple[bool, str]:
    """Python ÆÄÀÏÀÇ syntax Ã¼Å©"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code, filename=str(filepath))
        return True, ""
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def find_python_files(root: Path) -> List[Path]:
    """¸ðµç Python ÆÄÀÏ Ã£±â"""
    python_files = []
    exclude_dirs = {'__pycache__', '.git', 'node_modules', 'venv', 'env', '.venv'}
    
    for py_file in root.rglob('*.py'):
        # exclude __pycache__ and other directories
        if any(exclude in py_file.parts for exclude in exclude_dirs):
            continue
        python_files.append(py_file)
    
    return sorted(python_files)

def check_imports(filepath: Path, root: Path) -> List[str]:
    """ÆÄÀÏÀÇ import ¹® ºÐ¼®"""
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        
        tree = ast.parse(code, filename=str(filepath))
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    issues.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    issues.append(f"from {module} import {alias.name}")
    except Exception:
        pass
    
    return issues

def main():
    project_root = Path(__file__).parent.parent
    python_files = find_python_files(project_root)
    
    print(f"ÀüÃ¼ Python ÆÄÀÏ ¼ö: {len(python_files)}\n")
    print("=" * 80)
    print("¼Ò½ºÄÚµå ÆÄÀÏ Á¡°Ë °á°ú")
    print("=" * 80 + "\n")
    
    syntax_errors = []
    files_checked = 0
    
    for py_file in python_files:
        files_checked += 1
        relative_path = py_file.relative_to(project_root)
        
        is_valid, error_msg = check_syntax(py_file)
        
        if not is_valid:
            syntax_errors.append((relative_path, error_msg))
            print(f"[ERROR] {relative_path}")
            print(f"        {error_msg}\n")
        elif files_checked % 10 == 0:
            print(f"[OK] {files_checked}/{len(python_files)} files checked...")
    
    print("\n" + "=" * 80)
    print("Á¡°Ë ¿Ï·á")
    print("=" * 80)
    print(f"ÃÑ ÆÄÀÏ ¼ö: {len(python_files)}")
    print(f"Syntax ¿À·ù: {len(syntax_errors)}")
    
    if syntax_errors:
        print("\n[Syntax ¿À·ù ¸ñ·Ï]")
        for filepath, error in syntax_errors:
            print(f"  - {filepath}: {error}")
        return 1
    else:
        print("\n? ¸ðµç ÆÄÀÏÀÇ syntax °ËÁõ ¿Ï·á!")
        return 0

if __name__ == "__main__":
    sys.exit(main())

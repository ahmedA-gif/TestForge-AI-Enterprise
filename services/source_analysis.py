"""Bounded syntax checks of stored snapshots using bundled grammars."""
import ast
import json
import re
import tomllib
from pathlib import Path

from tree_sitter import Parser

from services.source_languages import DOCUMENT_EXTENSIONS, grammar_language, source_language


ANALYSIS_VERSION = 2
TEST_FILENAME = re.compile(
    r'(^test[_-]|[_-]test\.(py|go|rb|rs|sh)$|\.(test|spec)\.[cm]?[jt]sx?$|'
    r'(?:test|tests|spec)\.(java|kt|cs|swift|php|rb|cpp|c)$)', re.I
)


def syntax_findings(raw, path, language, grammar):
    check = f'{language} syntax'
    try:
        if grammar == 'python':
            ast.parse(raw, filename=path)
        elif grammar == 'json':
            json.loads(raw)
        elif grammar == 'toml':
            tomllib.loads(raw.decode('utf-8'))
        else:
            tree = Parser(grammar_language(grammar)).parse(raw)
            pending = [tree.root_node]
            issues = []
            while pending and len(issues) < 5:
                node = pending.pop()
                if node.is_error or node.is_missing:
                    row, column = node.start_point
                    issues.append({'path': path, 'line': row + 1, 'check': check,
                                   'message': f'Grammar error near column {column + 1}'})
                elif node.has_error:
                    pending.extend(reversed(node.children))
            return issues
    except (SyntaxError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        return [{'path': path, 'line': getattr(error, 'lineno', None) or 1,
                 'message': getattr(error, 'msg', str(error)), 'check': check}]
    except (UnicodeError, ValueError, RecursionError):
        return [{'path': path, 'line': 1, 'message': 'Unable to parse this file within supported encoding or nesting limits.', 'check': check}]
    return []


def analyze_source(root, files):
    issues, tests, syntax_checks, parsed_languages = [], [], {}, {}
    for file in files:
        relative = file['path']
        path = Path(root) / relative
        if TEST_FILENAME.search(path.name) or any(part.lower() in {'tests', '__tests__', 'spec'} for part in Path(relative).parts[:-1]):
            tests.append(relative)
        language, grammar = source_language(path.name)
        if grammar is None:
            continue
        try:
            raw = path.read_bytes()
            issues.extend(syntax_findings(raw, relative, language, grammar))
        except OSError:
            issues.append({'path': relative, 'line': 1, 'message': 'Snapshot file is unavailable.', 'check': 'File access'})
            continue
        syntax_checks[relative] = f'{language} syntax'
        parsed_languages[language] = parsed_languages.get(language, 0) + 1
    return {
        'version': ANALYSIS_VERSION, 'files': len(files), 'bytes': sum(file['size'] for file in files),
        'checked_files': len(syntax_checks), 'syntax_checks': syntax_checks, 'parsed_languages': parsed_languages,
        'issues': issues, 'test_files': tests,
        'documentation_files': sum(Path(file['path']).suffix.lower() in DOCUMENT_EXTENSIONS for file in files),
        'scope': 'Syntax checks use bundled parsers where available. File integrity checks cover the entire snapshot. Runtime execution uses an audited suite.',
    }

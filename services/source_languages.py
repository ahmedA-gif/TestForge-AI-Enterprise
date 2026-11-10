"""Filename-based language detection and bundled parser selection."""
from functools import lru_cache
from pathlib import Path
from importlib import import_module

from pygments.lexers import get_lexer_for_filename
from pygments.util import ClassNotFound
from tree_sitter import Language


GRAMMAR_MODULES = {
    'bash': ('tree_sitter_bash', 'language'),
    'c': ('tree_sitter_c', 'language'),
    'cpp': ('tree_sitter_cpp', 'language'),
    'csharp': ('tree_sitter_c_sharp', 'language'),
    'css': ('tree_sitter_css', 'language'),
    'go': ('tree_sitter_go', 'language'),
    'html': ('tree_sitter_html', 'language'),
    'java': ('tree_sitter_java', 'language'),
    'javascript': ('tree_sitter_javascript', 'language'),
    'kotlin': ('tree_sitter_kotlin', 'language'),
    'lua': ('tree_sitter_lua', 'language'),
    'php': ('tree_sitter_php', 'language_php'),
    'ruby': ('tree_sitter_ruby', 'language'),
    'rust': ('tree_sitter_rust', 'language'),
    'swift': ('tree_sitter_swift', 'language'),
    'typescript': ('tree_sitter_typescript', 'language_typescript'),
    'tsx': ('tree_sitter_typescript', 'language_tsx'),
    'yaml': ('tree_sitter_yaml', 'language'),
}
GRAMMARS = frozenset(GRAMMAR_MODULES) | {'python', 'json', 'toml'}
DOCUMENT_EXTENSIONS = frozenset({'.md', '.txt', '.rst', '.adoc'})
OVERRIDES = {
    '.py': ('Python', 'python'),
    '.json': ('JSON', 'json'),
    '.toml': ('TOML', 'toml'),
    '.js': ('JavaScript', 'javascript'),
    '.jsx': ('JavaScript', 'javascript'),
    '.mjs': ('JavaScript', 'javascript'),
    '.cjs': ('JavaScript', 'javascript'),
    '.ts': ('TypeScript', 'typescript'),
    '.mts': ('TypeScript', 'typescript'),
    '.cts': ('TypeScript', 'typescript'),
    '.tsx': ('TypeScript', 'tsx'),
    '.cs': ('C#', 'csharp'),
    '.h': ('C', 'c'),
    '.sh': ('Shell', 'bash'),
    '.bash': ('Shell', 'bash'),
    '.yml': ('YAML', 'yaml'),
    '.yaml': ('YAML', 'yaml'),
}


@lru_cache(maxsize=4096)
def source_language(filename):
    extension = Path(filename).suffix.lower()
    if extension in DOCUMENT_EXTENSIONS:
        return 'Document', None
    if extension in OVERRIDES:
        language, grammar = OVERRIDES[extension]
        return language, grammar if grammar in GRAMMARS else None
    try:
        lexer = get_lexer_for_filename(filename)
    except ClassNotFound:
        return 'Other text', None
    aliases = (alias.lower().replace('-', '_') for alias in lexer.aliases)
    grammar = next((alias for alias in aliases if alias in GRAMMARS), None)
    return lexer.name, grammar


@lru_cache(maxsize=256)
def grammar_language(grammar):
    module, factory = GRAMMAR_MODULES[grammar]
    return Language(getattr(import_module(module), factory)())

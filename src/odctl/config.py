import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

# Workspace directory requested via the global `--workspace` flag (set in main.py).
_workspace_override: Optional[Path] = None


def set_workspace_override(path: Optional[Path]) -> None:
    """
    Record the workspace directory requested via the global `--workspace` flag.

    Args:
        path (Optional[Path]): The folder given to `--workspace`, or None for the default.
    """
    global _workspace_override
    _workspace_override = path.resolve() if path is not None else None


def get_internal_resources_dir() -> Path:
    """
    Determine the path to the bundled compose files, supporting PyInstaller.

    Returns:
        Path: The absolute path to the internal `resources` directory.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running as a compiled PyInstaller binary
        return Path(sys._MEIPASS) / "odctl" / "resources"
    # Running as a normal Python script
    return Path(__file__).parent.resolve() / "resources"


# Internal immutable resources bundled with the CLI
INTERNAL_RESOURCES_DIR = get_internal_resources_dir()


def get_workspace_dir() -> Path:
    """
    Get the path to the local mutable workspace.

    Returns:
        Path: The directory supplied via `--workspace`, or the `.odctl` directory in
        the current working directory when no override is set.
    """
    if _workspace_override is not None:
        return _workspace_override
    return Path.cwd() / ".odctl"


def get_active_dir() -> Path:
    """
    Determine the active configuration directory.

    Returns:
        Path: The local workspace directory if it exists; otherwise, falls back
        to the internal resources directory.
    """
    workspace = get_workspace_dir()
    return workspace if workspace.exists() else INTERNAL_RESOURCES_DIR


def get_registry_path() -> Path:
    """
    Get the path to the stack registry configuration file.

    Returns:
        Path: The path to `registry.yml` within the active directory.
    """
    return get_active_dir() / "registry.yml"


def get_compose_path(filename: str) -> Path:
    """
    Get the path to a specific docker-compose file.

    Args:
        filename (str): The name of the compose file (for example, 'compose-infra.yml').

    Returns:
        Path: The path to the requested file within the active directory.
    """
    return get_active_dir() / filename


class UnreadableFileError(ValueError):
    """A file odctl needs cannot be read. The message names the file and the reason."""


class _ComposeLoader(yaml.SafeLoader):
    """PyYAML's safe loader, reading a compose file as Compose reads it.

    Compose drops a node tagged `!reset` before it resolves merge keys, and keeps a
    node tagged `!override` as written (compose-go loader/reset.go, `resolveReset`).
    `safe_load` refuses both tags, so a file Compose runs would not be readable.

    Compose's YAML library (go-yaml v4, resolver.go) also reads plain values by
    YAML 1.2 rules, which `_go_scalar` follows: only `true` and `false` in three
    spellings are booleans, so `yes`, `on` and `off` are strings, and an int has no
    `:` part, so `2222:22` is a string where YAML 1.1 reads the base 60 integer
    133342.
    """

    def flatten_mapping(self, node: yaml.MappingNode) -> None:
        # Why: Compose drops a `!reset` key in every mapping, merge sources included,
        # before merge keys apply, so a merged `<<` value fills it
        node.value = [(k, v) for k, v in node.value if v.tag != "!reset"]
        super().flatten_mapping(node)

    def resolve(self, kind: Any, value: Any, implicit: Any) -> str:
        if kind is yaml.ScalarNode and implicit[0]:
            tag = _go_scalar(value)[0]
            if tag is not None:
                return tag
            resolved = super().resolve(kind, value, implicit)
            if resolved in _GO_TAGS:
                return "tag:yaml.org,2002:str"
            if resolved == _TIMESTAMP:
                # Why: go-yaml keeps a plain value as text when time.Parse rejects
                # it, such as 2026-02-30
                try:
                    self.construct_yaml_timestamp(yaml.ScalarNode(resolved, value))
                except (AttributeError, ValueError):
                    return "tag:yaml.org,2002:str"
            return resolved
        return super().resolve(kind, value, implicit)


_BOOL = "tag:yaml.org,2002:bool"
_INT = "tag:yaml.org,2002:int"
_FLOAT = "tag:yaml.org,2002:float"
_TIMESTAMP = "tag:yaml.org,2002:timestamp"
_GO_TAGS = {_BOOL, _INT, _FLOAT}
_GO_WORDS: Dict[str, Any] = {
    **dict.fromkeys(["true", "True", "TRUE"], True),
    **dict.fromkeys(["false", "False", "FALSE"], False),
    **dict.fromkeys([".nan", ".NaN", ".NAN"], float("nan")),
    **dict.fromkeys([".inf", ".Inf", ".INF", "+.inf", "+.Inf", "+.INF"], float("inf")),
    **dict.fromkeys(["-.inf", "-.Inf", "-.INF"], float("-inf")),
    **dict.fromkeys(["-0", "-0.0"], -0.0),
}
# Go's strconv.ParseInt with base 0, after go-yaml removes every `_`
_GO_INT = re.compile(
    r"([-+]?)(?:0[xX]([0-9a-fA-F]+)|0[oO]([0-7]+)|0[bB]([01]+)|0([0-7]*)|([1-9][0-9]*))"
)
_GO_FLOAT = re.compile(r"[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?")


def _go_scalar(text: str) -> Tuple[Optional[str], Any]:
    """Read a plain scalar as go-yaml v4 does, for booleans and numbers.

    Follows `resolve` in go-yaml's resolver.go: a fixed word list, then for text
    that starts with a digit or a sign an int by Go's base 0 rules within 64 bits
    (`017` is octal 15, `0x1F` is 31), then a float (`0930` is 930.0). A leading
    `.` is tried as a float as written.

    Args:
        text (str): The scalar as written.

    Returns:
        Tuple[Optional[str], Any]: The YAML tag and the value, or (None, None) when
        go-yaml reads the text as something other than a boolean or a number.
    """
    if text in _GO_WORDS:
        value = _GO_WORDS[text]
        return (_BOOL if isinstance(value, bool) else _FLOAT), value
    if text[:1] == ".":
        try:
            number = float(text)
        except ValueError:
            return None, None
        # Why: Go's ParseFloat reports a value past the float range as an error, and
        # go-yaml then keeps the text as a string
        return (_FLOAT, number) if abs(number) != float("inf") else (None, None)
    if text[:1] not in set("+-0123456789"):
        return None, None
    plain = text.replace("_", "")
    match = _GO_INT.fullmatch(plain)
    if match:
        sign, hexa, octal, binary, zero, decimal = match.groups()
        if hexa is not None:
            number = int(hexa, 16)
        elif octal is not None:
            number = int(octal, 8)
        elif binary is not None:
            number = int(binary, 2)
        elif zero is not None:
            number = int(zero or "0", 8)
        else:
            number = int(decimal)
        number = -number if sign == "-" else number
        if -(2**63) <= number < 2**64:
            return _INT, number
    if _GO_FLOAT.fullmatch(plain) and abs(float(plain)) != float("inf"):
        return _FLOAT, float(plain)
    return None, None


def _construct_go_number(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> Any:
    tag, value = _go_scalar(loader.construct_scalar(node))
    # Why: go-yaml gives a float for `!!float 5`, and refuses an `!!int` value that
    # is not an int (resolver.go, the deferred check in `resolve`)
    if tag == _INT and node.tag == _FLOAT:
        return float(value)
    if tag != node.tag:
        raise yaml.constructor.ConstructorError(
            None, None, f"cannot read {node.value!r} as {node.tag}", node.start_mark
        )
    return value


_ComposeLoader.add_constructor(_BOOL, _construct_go_number)
_ComposeLoader.add_constructor(_INT, _construct_go_number)
_ComposeLoader.add_constructor(_FLOAT, _construct_go_number)


def _construct_go_null(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> None:
    # Why: go-yaml reads only these words as null, and refuses `!!null` on others
    if loader.construct_scalar(node) not in ("", "~", "null", "Null", "NULL"):
        raise yaml.constructor.ConstructorError(
            None, None, f"cannot read {node.value!r} as {node.tag}", node.start_mark
        )
    return None


_ComposeLoader.add_constructor("tag:yaml.org,2002:null", _construct_go_null)


def _construct_timestamp(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> Any:
    # Why: PyYAML raises AttributeError for `!!timestamp` on text that is not one
    try:
        return yaml.SafeLoader.construct_yaml_timestamp(loader, node)
    except (AttributeError, ValueError) as e:
        raise yaml.constructor.ConstructorError(
            None, None, f"cannot read {node.value!r} as {node.tag}", node.start_mark
        ) from e


_ComposeLoader.add_constructor(_TIMESTAMP, _construct_timestamp)


_RESET = object()


def _construct_reset(loader: yaml.SafeLoader, node: yaml.Node) -> object:
    return _RESET


def _construct_override(loader: yaml.SafeLoader, node: yaml.Node) -> Any:
    # Why: go-yaml keeps a scalar with a tag it does not know as its text
    if isinstance(node, yaml.ScalarNode):
        return node.value
    # Why: a copy with the plain tag, because the tagged node is still being built
    plain = type(node)(
        loader.resolve(type(node), None, (True, False)),
        node.value,
        node.start_mark,
        node.end_mark,
    )
    return loader.construct_object(plain, deep=True)


_ComposeLoader.add_constructor("!reset", _construct_reset)
_ComposeLoader.add_constructor("!override", _construct_override)


def _drop_reset(value: Any) -> Any:
    """Returns the value without the nodes tagged `!reset`, at any depth."""
    if value is _RESET:
        return None
    if isinstance(value, dict):
        return {k: _drop_reset(v) for k, v in value.items() if v is not _RESET}
    if isinstance(value, list):
        return [_drop_reset(v) for v in value if v is not _RESET]
    return value


def read_yaml(path: Path, name: str) -> Any:
    """
    Read a YAML file that odctl needs, such as a compose file or `registry.yml`.

    Args:
        path (Path): The file to read.
        name (str): How the error message names the file.

    Returns:
        Any: The file's content, read as Compose reads it (`_ComposeLoader`).

    Raises:
        UnreadableFileError: As `Cannot read <name>: <reason>`, when the file is
            missing, cannot be opened, is not UTF-8 text, or is not valid YAML.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _drop_reset(yaml.load(f, Loader=_ComposeLoader))
    except FileNotFoundError as e:
        raise UnreadableFileError(
            f"Cannot read {name}: the file does not exist."
        ) from e
    except OSError as e:
        raise UnreadableFileError(f"Cannot read {name}: {e.strerror}.") from e
    except UnicodeDecodeError as e:
        raise UnreadableFileError(f"Cannot read {name}: it is not UTF-8 text.") from e
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        where = f" (line {mark.line + 1})" if mark else ""
        raise UnreadableFileError(
            f"Cannot read {name}: it is not valid YAML{where}."
        ) from e


# Compose interpolation, in every form the Compose specification and Docker's docs
# list, because a workspace file may use any of them: $VAR, ${VAR}, the operators
# :- - :? ? :+ +, a word that holds another reference, and $$ for a literal $.
_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_BRACED_REFERENCE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:(:?[-?+])(.*))?", re.S)

# What compose-go's dotenv parser treats as a space within a line (`isSpace` in
# dotenv/parser.go): every space character but the line break.
_ENV_SPACES = "\t\v\f\r \x85\xa0"

# The escapes Compose applies in a double-quoted value (`escapeSeqRegex`).
_ENV_ESCAPE = re.compile(r'\\(?:[abcfnrtv$"\\]|0\d{0,3})')
_ENV_ESCAPED = {
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "$": "$$",
    '"': '"',
    "\\": "\\",
}


class _EnvLineError(Exception):
    """A statement of a `.env` file that Compose rejects."""


def _env_escape(match: re.Match) -> str:
    """
    Apply one escape of a double-quoted `.env` value, as `expandEscapes` does.

    Args:
        match (re.Match): A match of `_ENV_ESCAPE`.

    Returns:
        str: The character. `\\$` gives `$$`, which interpolation turns into `$`. An
        octal escape needs `\\0` and three octal digits, at most `\\0377`; any other
        loses its `0`, because Compose rewrites `\\0` to `\\` before Go's
        `strconv.UnquoteChar` rejects it. `\\c`, which UnquoteChar also rejects, is
        kept as written.
    """
    text = match.group(0)
    if text[1] != "0":
        return _ENV_ESCAPED.get(text[1], text)
    digits = text[2:]
    if len(digits) == 3 and all(d in "01234567" for d in digits):
        if int(digits, 8) <= 0o377:
            return chr(int(digits, 8))
    return "\\" + digits


def _env_key(src: str) -> Tuple[str, str, bool]:
    """
    Read the key that starts a `.env` statement, as `locateKeyName` does.

    Args:
        src (str): The file from the start of the statement.

    Returns:
        Tuple[str, str, bool]: The key; the text after its `=`, `:` or line break, with
        the spaces before the value removed; and True when the key stands alone on
        its line, so its value comes from the environment.

    Raises:
        _EnvLineError: When the key holds a character other than letters, digits,
            `_`, `.`, `-`, `[` and `]`.
    """
    if re.match(r"export[\t\n\f\r ]", src):
        src = src[len("export") :].lstrip(_ENV_SPACES)
    for index, char in enumerate(src):
        if char in _ENV_SPACES:
            continue
        if char in "=:\n":
            rest = src[index + 1 :].lstrip(_ENV_SPACES)
            return src[:index].rstrip(), rest, char == "\n"
        if not (char in "_.-[]" or char.isalpha() or char.isnumeric()):
            raise _EnvLineError(char)
    return src.rstrip(), "", True


def _env_value(src: str, env: Dict[str, str]) -> Tuple[str, str]:
    """
    Read the value of a `.env` statement, as `extractVarValue` does.

    An unquoted value ends at the line break, loses an inline comment that follows a
    space, and is interpolated. A single-quoted value is kept as written, and a
    double-quoted one gets its escapes and is interpolated; both can span lines,
    and a backslash before the quote keeps it in the value.

    Args:
        src (str): The file from the start of the value.
        env (Dict[str, str]): The variables interpolation reads.

    Returns:
        Tuple[str, str]: The value, and the text after it.

    Raises:
        _EnvLineError: When a quoted value has no closing quote.
    """
    if not src or src[0] not in "\"'":
        value, _, rest = src.partition("\n")
        value = value.split(" #", 1)[0].rstrip()
        return expand(value, env), rest

    quote = src[0]
    chars = []
    escaped = False
    for index in range(1, len(src)):
        char = src[index]
        if char != quote:
            if not escaped and char == "\\":
                escaped = True
                continue
            if escaped:
                escaped = False
                chars.append("\\")
            chars.append(char)
            continue
        if escaped:
            escaped = False
            chars.append(char)
            continue
        value = "".join(chars)
        if quote == '"':
            value = expand(_ENV_ESCAPE.sub(_env_escape, value), env)
        return value, src[index + 1 :]
    raise _EnvLineError(quote)


def read_env_file(path: Path) -> Dict[str, str]:
    """
    Parse a compose `.env` file into a plain dictionary, as Compose reads it.

    The rules are those of compose-go's dotenv parser (dotenv/parser.go), the code
    Compose runs. `#` starts a comment line. A key is followed by `=` or `:`, and
    `export ` before it is dropped. A later line overrides an earlier one. Values
    are read by `_env_value`, and interpolation reads the shell environment first,
    then the lines above (dotenv/godotenv.go, `expandVariables`). A key alone on
    its line takes its value from the shell environment. Compose stops at a line it
    rejects; odctl reads the file only to show and check what Compose will run, so
    it skips that line and reads on, and Compose reports the line when it runs.

    Args:
        path (Path): Path to the `.env` file. A missing file, or one that cannot be
            read, yields an empty mapping.

    Returns:
        Dict[str, str]: The declared variables, with their values as Compose reads them.
    """
    values: Dict[str, str] = {}
    try:
        data = path.read_bytes()
    except OSError:
        return values

    # compose-go reads bytes and drops a UTF-8 byte order mark (dotenv/godotenv.go,
    # parseWithLookup); a byte that is not UTF-8 stays inside its value.
    src = data.decode("utf-8", errors="replace").removeprefix("\ufeff")
    while True:
        src = src.lstrip()
        while src.startswith("#"):
            _, newline, src = src.partition("\n")
            src = src.lstrip() if newline else ""
        if not src:
            return values
        try:
            key, rest, inherited = _env_key(src)
            if not key or " " in key:
                raise _EnvLineError(key)
            if inherited:
                if key in os.environ:
                    values[key] = os.environ[key]
            else:
                values[key], rest = _env_value(rest, {**values, **os.environ})
            src = rest
        except _EnvLineError:
            src = src.partition("\n")[2]


def expand(value: str, env: Dict[str, str]) -> str:
    """
    Substitute compose variables in a string.

    Args:
        value (str): A raw value from a compose file, such as an image reference.
        env (Dict[str, str]): The variables to substitute.

    Returns:
        str: The value with every variable reference replaced. A reference that is
            not valid Compose syntax is kept as written.
    """
    parts = []
    i = 0
    while i < len(value):
        if value[i] != "$":
            parts.append(value[i])
            i += 1
        elif value.startswith("$$", i):
            parts.append("$")
            i += 2
        elif value.startswith("${", i):
            end = _closing_brace(value, i + 2)
            if end is None:
                parts.append(value[i:])
                break
            parts.append(_substitute(value[i + 2 : end], env))
            i = end + 1
        elif name := _VARIABLE_NAME.match(value, i + 1):
            parts.append(env.get(name.group(0)) or "")
            i = name.end()
        else:
            parts.append("$")
            i += 1
    return "".join(parts)


def _closing_brace(value: str, start: int) -> Optional[int]:
    """
    Find the brace that closes a `${` reference, past any reference nested in it.

    Args:
        value (str): The string being expanded.
        start (int): The index just after the opening `${`.

    Returns:
        Optional[int]: The index of the closing brace, or None when there is none.
    """
    depth = 1
    for index in range(start, len(value)):
        if value[index] == "{":
            depth += 1
        elif value[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _substitute(reference: str, env: Dict[str, str]) -> str:
    """
    Return the value of one braced reference, the text between `${` and `}`.

    The `:?` and `?` forms make Compose stop with an error when they do not hold.
    odctl only shows the value, so it shows an empty one instead.

    Args:
        reference (str): The name, then optionally an operator and its word.
        env (Dict[str, str]): The variables to substitute.

    Returns:
        str: The value the operator selects. The word is expanded too, so it can
            hold another reference.
    """
    match = _BRACED_REFERENCE.fullmatch(reference)
    if not match:
        return "${" + reference + "}"
    name, operator, word = match.groups()
    current = env.get(name)
    # The operators with a colon test for a non-empty value, the others for a set one.
    holds = (
        bool(current) if operator is None or ":" in operator else current is not None
    )
    if operator in (None, ":?", "?"):
        return (current or "") if holds else ""
    if operator in (":-", "-"):
        return (current or "") if holds else expand(word, env)
    return expand(word, env) if holds else ""

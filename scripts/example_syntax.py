"""Bounded declaration reader for example policy, not an HCL evaluator/parser.

Keep expressions opaque except literal policy fields and filesystem calls. Native
CLIs own language validation. Unsupported/ambiguous declaration shapes fail closed.
"""

from dataclasses import dataclass, field
import json
import re


@dataclass
class Token:
    kind: str
    value: object


class Reader:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def template(self, quoted=False, depth=0):
        result = []
        literal = True
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if quoted and char == '"':
                self.pos += 1
                return ''.join(result) if literal else None
            if quoted and char in '\r\n':
                raise ValueError("Unterminated quoted string; boundary review required.")
            if quoted and char == '\\':
                self.pos += 1
                escape = self.text[self.pos:self.pos + 1]
                simple = {'n': '\n', 'r': '\r', 't': '\t', '"': '"', '\\': '\\'}
                if escape in simple:
                    result.append(simple[escape])
                    self.pos += 1
                elif escape in ('u', 'U'):
                    size = 4 if escape == 'u' else 8
                    code = self.text[self.pos + 1:self.pos + 1 + size]
                    if len(code) != size or not re.fullmatch('[0-9a-fA-F]+', code):
                        raise ValueError("Invalid Unicode escape; boundary review required.")
                    result.append(chr(int(code, 16)))
                    self.pos += size + 1
                else:
                    raise ValueError("Invalid string escape; boundary review required.")
            elif self.text.startswith(('$${', '%%{'), self.pos):
                result.append(self.text[self.pos + 1:self.pos + 3])
                self.pos += 3
            elif self.text.startswith(('${', '%{'), self.pos):
                literal = False
                self.pos += 2
                self.tokens('}', depth + 1)
            else:
                result.append(char)
                self.pos += 1
        if quoted:
            raise ValueError("Unterminated quoted string; boundary review required.")
        return ''.join(result) if literal else None

    def tokens(self, closing=None, depth=0):
        if depth > 64:
            raise ValueError("Syntax nesting exceeds the example boundary review limit.")
        result = []
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == closing:
                self.pos += 1
                return result
            if char in '})]':
                raise ValueError("Unbalanced syntax; boundary review required.")
            if char in ' \t\r':
                self.pos += 1
                continue
            if self.text.startswith(('//', '#'), self.pos):
                end = self.text.find('\n', self.pos)
                self.pos = len(self.text) if end < 0 else end
                continue
            if self.text.startswith('/*', self.pos):
                end = self.text.find('*/', self.pos + 2)
                if end < 0:
                    raise ValueError("Unterminated comment; boundary review required.")
                if '\n' in self.text[self.pos:end]:
                    result.append(Token('\n', '\n'))
                self.pos = end + 2
                continue
            if self.text.startswith('<<', self.pos):
                raise ValueError("Heredoc requires an explicit example-boundary review.")
            if self.text[self.pos:self.pos + 2] in ("==", "!=", "<=", ">=", "=>"):
                result.append(Token("operator", self.text[self.pos:self.pos + 2]))
                self.pos += 2
                continue
            self.pos += 1
            if char == '"':
                token = Token('string', self.template(quoted=True, depth=depth))
            elif char in '{[(':
                token = Token(char, self.tokens({'{': '}', '[': ']', '(': ')'}[char], depth + 1))
            elif char.isalpha() or char == '_':
                start = self.pos - 1
                while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] in '_-'):
                    self.pos += 1
                token = Token('id', self.text[start:self.pos])
            else:
                token = Token(char, char)
            previous = next((t for t in reversed(result) if t.kind != '\n'), None)
            if (token.kind == '(' and previous and previous.kind == 'id'
                    and re.fullmatch(r'file[a-z0-9]*|templatefile', previous.value)):
                raise ValueError("Filesystem function requires a copy-boundary review.")
            result.append(token)
        if closing:
            raise ValueError("Unterminated expression/block; boundary review required.")
        return result


@dataclass
class Body:
    attrs: dict = field(default_factory=dict)
    blocks: list = field(default_factory=list)


@dataclass
class Expression:
    value: object
    is_json: bool = False

    def literal(self):
        if self.is_json:
            return Reader(self.value).template() if isinstance(self.value, str) else None
        parts = [t for t in self.value if t.kind != '\n']
        return parts[0].value if len(parts) == 1 and parts[0].kind == 'string' else None

    def object_attrs(self):
        if self.is_json and isinstance(self.value, dict):
            return {name: Expression(value, True) for name, value in self.value.items()}
        if not self.is_json and len(self.value) == 1 and self.value[0].kind == '{':
            return hcl_body(self.value[0].value, object_only=True).attrs
        raise ValueError("Provider requirement must be a literal object; execution-policy review required.")


def hcl_body(parts, object_only=False):
    body = Body()
    i = 0
    while i < len(parts):
        if parts[i].kind == '\n' or (object_only and parts[i].kind == ','):
            i += 1
            continue
        name = parts[i]
        if name.kind != 'id' and not (object_only and name.kind == 'string' and name.value is not None):
            raise ValueError("Ambiguous declaration; boundary review required.")
        i += 1
        if i < len(parts) and parts[i].kind in (('=', ':') if object_only else ('=',)):
            i += 1
            start = i
            while i < len(parts) and parts[i].kind not in (('\n', ',') if object_only else ('\n',)):
                if parts[i].kind == '=':
                    raise ValueError("Ambiguous attribute boundary; review required.")
                i += 1
            if i == start or name.value in body.attrs:
                raise ValueError("Empty or duplicate attribute; boundary review required.")
            body.attrs[name.value] = Expression(parts[start:i])
        else:
            labels = []
            while i < len(parts) and parts[i].kind in ('id', 'string') and parts[i].value is not None:
                labels.append(parts[i].value)
                i += 1
            if object_only or i == len(parts) or parts[i].kind != '{':
                raise ValueError("Unsupported declaration shape; boundary review required.")
            body.blocks.append((name.value, labels, hcl_body(parts[i].value)))
            i += 1
    return body


# Only declaration positions in these schemas interpret names as block types.
# Attribute objects, labels and strings never become declarations.
SCHEMAS = {
    'source': {'terraform': 0, 'locals': 0, 'variable': 1, 'output': 1, 'resource': 2, 'module': 1, 'provider': 1, 'check': 1},
    'tests': {'run': 1, 'variables': 0, 'provider': 1, 'test': 0},
    'terraform': {'required_providers': 0},
    'variable': {'validation': 0},
    'output': {'precondition': 0},
    'resource': {'lifecycle': 0},
    'lifecycle': {'precondition': 0, 'postcondition': 0},
    'check': {'assert': 0},
    'run': {'variables': 0, 'assert': 0, 'plan_options': 0},
}
# JSON has no syntactic distinction between an attribute object and a block.
# Bound ambiguous keys to the actual reviewed block schemas, not a keyword denylist.
JSON_ATTRS = {
    'source': set(), 'tests': set(), 'check': set(),
    'terraform': {'required_version'},
    'variable': {'type', 'default', 'description', 'sensitive', 'nullable', 'ephemeral'},
    'output': {'value', 'description', 'sensitive', 'depends_on', 'ephemeral'},
    'resource': {'length', 'prefix', 'separator', 'keepers', 'count', 'for_each', 'provider', 'depends_on'},
    'provider': {'alias'},
    'lifecycle': {'create_before_destroy', 'prevent_destroy', 'ignore_changes', 'replace_triggered_by'},
    'run': {'command', 'expect_failures', 'providers', 'state_key', 'parallel'},
    'test': {'parallel'},
    'plan_options': {'mode', 'refresh', 'replace', 'target'},
    **{name: {'condition', 'error_message'} for name in ('assert', 'validation', 'precondition', 'postcondition')},
}


def json_expression(value):
    if isinstance(value, str):
        Reader(value).template()
    elif isinstance(value, list):
        for item in value:
            json_expression(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            # JSON expression object keys are templates too.
            Reader(key).template()
            json_expression(item)


def json_body(value, context):
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON block object; boundary review required.")
    body = Body()
    schema = SCHEMAS.get(context, {})
    for name, item in value.items():
        if name == '//':  # HCL JSON comment property, not an expression.
            continue
        if name in schema:
            def blocks(item, labels):
                if isinstance(item, list):
                    for child in item:
                        blocks(child, labels)
                elif len(labels) < schema[name] and isinstance(item, dict):
                    for label, child in item.items():
                        blocks(child, labels + [label])
                elif len(labels) == schema[name]:
                    body.blocks.append((name, labels, json_body(item, name)))
                else:
                    raise ValueError("Invalid JSON block labels; boundary review required.")
            blocks(item, [])
        elif context in JSON_ATTRS and name not in JSON_ATTRS[context]:
            raise ValueError(f"{name} is outside the reviewed execution-policy declarations.")
        else:
            # Terraform JSON's variable defaults are literal JSON values, unlike
            # locals/outputs. Template-looking text here cannot read a file.
            literal_metadata = (
                (context == 'variable' and name in ('default', 'type'))
                or (context in ('variable', 'output') and name == 'description')
            )
            if not literal_metadata:
                json_expression(item)
            body.attrs[name] = Expression(item, True)
    return body


def read_body(path, is_test=False):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key; boundary review required.")
            result[key] = value
        return result

    try:
        text = path.read_text()
        if path.name.endswith('.json'):
            return json_body(json.loads(text, object_pairs_hook=unique_pairs), 'tests' if is_test else 'source')
        return hcl_body(Reader(text).tokens())
    except (ValueError, RecursionError) as error:
        raise ValueError(f"{path}: {error}") from error

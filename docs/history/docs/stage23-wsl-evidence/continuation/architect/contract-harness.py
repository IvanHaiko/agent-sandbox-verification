"""Frozen prior labels contract and Controller harness; no legacy transport imports."""
import ast
import json
from pathlib import Path
import jsonschema


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Non-finite JSON value')
    return json.loads(data, object_pairs_hook=pairs, parse_constant=constant)


def validate_design(data):
    design = strict_json(data.decode('utf-8'))
    jsonschema.Draft202012Validator(DESIGN_SCHEMA).validate(design)
    cases = design['cases']
    if len({case['id'] for case in cases}) != len(cases):
        raise ValueError('Duplicate case IDs')
    if not all(case['input'].isascii() and (case['expected'] is None or
               all(item.isascii() for item in case['expected'])) for case in cases):
        raise ValueError('Test exceeds the ASCII domain')
    if len({case['input'] for case in cases}) != len(cases):
        raise ValueError('Duplicate test inputs')
    return {'valid': True, 'case_count': len(cases), 'schema_valid': True,
            'ascii_domain_valid': True, 'unique_ids': True}


def validate_candidate(data):
    tree = ast.parse(data.decode('utf-8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == 'normalize_labels']
    if len(functions) != 1:
        raise ValueError('Public function missing or duplicated')
    function = functions[0]
    args = function.args
    valid = (len(args.args) == 1 and args.args[0].arg == 'value' and not args.posonlyargs
             and not args.vararg and not args.kwarg and not args.kwonlyargs
             and not args.defaults and not function.decorator_list
             and ast.unparse(args.args[0].annotation) in ('str', "'str'", '"str"')
             and ast.unparse(function.returns) in ('list[str]', "'list[str]'", '"list[str]"'))
    if not valid:
        raise ValueError('Public interface mismatch')
    compile(tree, TASK['file'], 'exec')
    return {'valid': True, 'public_interface_verified': True, 'syntax_verified': True}

TASK_ID = 'STAGE20-LABELS'

CRITERIA = [
    'Scan ASCII strings left to right. An unescaped comma outside double quotes ends a label; repeated separators are allowed.',
    'An unescaped double quote toggles quoted mode anywhere within a label; quote delimiters are removed and adjacent quoted/unquoted text concatenates.',
    'Backslash escapes exactly the next character in either mode: remove the backslash, preserve the next character literally, and do not treat it as a quote or separator.',
    'A trailing unpaired backslash or unclosed double quote raises ValueError for the whole input, even after otherwise valid labels.',
    'Only ASCII whitespace (space, tab, CR, LF, vertical tab, form feed) that was neither quoted nor escaped is ordinary whitespace.',
    'Trim ordinary whitespace from each label boundary before collapsing internal ordinary-whitespace runs to one ASCII space.',
    'Quoted or escaped whitespace is protected: preserve its exact characters and multiplicity, including at label boundaries; it also breaks ordinary-whitespace runs.',
    'Lowercase ASCII A-Z in all emitted characters; preserve other non-delimiter literal characters exactly.',
    'After parsing and normalization, discard labels whose resulting string is empty. Whitespace-only protected labels are nonempty and retained.',
    'Deduplicate normalized strings by exact equality, retaining first occurrence order. Empty input returns an empty list.'
]

TASK = {'task_id': TASK_ID, 'contract_version': 1,
    'public_interface': 'def normalize_labels(value: str) -> list[str]',
    'file': 'src/normalize_labels.py', 'acceptance_criteria': CRITERIA,
    'constraints': ['Pure Python, standard library only, no external dependencies or I/O.',
        'ASCII string inputs are in scope; Unicode and non-string behavior are unspecified.',
        'Do not add features or mutate any file other than src/normalize_labels.py.']}

def schema(properties):
    properties = {'task_id': {'type': 'string', 'const': TASK_ID},
                  'contract_version': {'type': 'integer', 'const': 1}, **properties}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

STR = {'type': 'string', 'minLength': 1, 'maxLength': 2000}

CASE_SCHEMA = {'type': 'object', 'properties': {'id': STR, 'intent': STR,
    'input': {'type': 'string', 'maxLength': 1000},
    'expected': {'type': ['array','null'], 'items': {'type':'string','maxLength':1000}, 'maxItems':100}},
    'required': ['id', 'intent', 'input', 'expected'], 'additionalProperties': False}

DESIGN_SCHEMA = schema({'cases': {'type': 'array', 'minItems': 10, 'maxItems': 24, 'items': CASE_SCHEMA},
    'properties': {'type': 'array', 'uniqueItems': True, 'maxItems': 2,
        'items': {'type': 'string', 'enum': ['unique_nonempty_labels', 'ascii_lowercase']}},
    'rationale': STR})

def acceptance_source(design):
    # Only the frozen Tester data selects cases, expectations and properties.
    return '''import inspect,json,sys,runpy
normalize_labels = runpy.run_path('src/normalize_labels.py')['normalize_labels']
DESIGN = json.loads(''' + repr(json.dumps(design)) + ''')
results=[]; properties=[]; interface=True
s=inspect.signature(normalize_labels)
interface=(list(s.parameters)==['value'] and s.parameters['value'].annotation in (str,'str') and s.return_annotation in (list[str],'list[str]'))
for c in DESIGN['cases']:
    actual=None; error=None
    try: actual=normalize_labels(c['input'])
    except Exception as exc: error=type(exc).__name__
    passed=(error=='ValueError') if c['expected'] is None else (error is None and type(actual) is list and actual==c['expected'])
    results.append({'id':c['id'],'input':c['input'],'expected':c['expected'],'actual':actual,'error':error,'passed':passed})
    if error is None and type(actual) is list:
        for prop in DESIGN['properties']:
            ok=(all(type(x) is str and x!='' for x in actual) and len(actual)==len(set(actual))) if prop=='unique_nonempty_labels' else all(type(x) is str and not any('A'<=ch<='Z' for ch in x) for x in actual)
            properties.append({'case':c['id'],'property':prop,'passed':ok})
passed=interface and all(c['passed'] for c in results) and all(c['passed'] for c in properties)
print(json.dumps({'passed':passed,'interface':interface,'cases':results,'properties':properties},ensure_ascii=True))
sys.exit(0 if passed else 1)
'''

def contract_interpret(value):
    """Controller contract-consistency check; never supplies acceptance expectations.
    Written before the run; used only to classify a failing frozen case."""
    tokens=[]; current=[]; quoted=False; escape=False
    for ch in value:
        if escape:
            current.append((ch,True)); escape=False
        elif ch==chr(92): escape=True
        elif ch=='"': quoted=not quoted
        elif ch==',' and not quoted: tokens.append(current); current=[]
        else: current.append((ch,quoted))
    if escape or quoted: raise ValueError()
    tokens.append(current); result=[]
    ordinary=lambda item: not item[1] and item[0] in ' \t\r\n\v\f'
    for token in tokens:
        while token and ordinary(token[0]): token=token[1:]
        while token and ordinary(token[-1]): token=token[:-1]
        chars=[]; in_run=False
        for ch,protected in token:
            if ordinary((ch,protected)):
                if not in_run: chars.append(' ')
                in_run=True
            else:
                chars.append(chr(ord(ch)+32) if 'A'<=ch<='Z' else ch); in_run=False
        label=''.join(chars)
        if label and label not in result: result.append(label)
    return result

def classify_failures(execution, design):
    by_id={c['id']:c for c in design['cases']}
    classified=[]
    for failure in execution['cases']:
        if failure['passed']: continue
        c=by_id[failure['id']]
        try: expected=contract_interpret(c['input'])
        except ValueError: expected=None
        kind='implementation_defect' if expected==c['expected'] else 'test_defect'
        classified.append({**failure,'classification':kind,'contract_expected':expected,
            'basis':'Contract rules 1-10; Controller interpreter preserved in executed-driver.py before candidate creation.'})
    if not execution['interface'] or any(not p['passed'] for p in execution['properties']):
        classified.append({'classification':'implementation_defect','basis':'Required interface or selected contract-derived output invariant failed.'})
    return classified

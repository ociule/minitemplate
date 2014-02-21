"""
This is a toy template engine, following the specification on http://pythonpracticeprojects.com/templating-engine.html

The template engine is a compiler, so it has the three classic steps of a compile pipeline:
 - tokenize
 - parse
 - eval
Each step is implemented in a separate function which has the same name as the step.
"""

import re
import math 


EXPRESSION_START = "{{"
EXPRESSION_END = "}}"
STATEMENT_START = "{%"
STATEMENT_END = "%}"
TOKEN_REGEX = re.compile(r"(%s.*?%s|%s.*?%s)" % (EXPRESSION_START, EXPRESSION_END, STATEMENT_START, STATEMENT_END))
_GLOBAL_ENV = {
    'statements': {
        'len': lambda x, data_model: len(x),
    },
    'variables': {},
    'operators': {
        'binary': {
            '+': lambda x, y: x+y,
            '-': lambda x, y: x-y,
            '*': lambda x, y: x*y,
            '/': lambda x, y: float(x)/y,
            '/': lambda x, y: x % y,
            '>': lambda x, y: x > y,
            '<': lambda x, y: x < y,
            '>=': lambda x, y: x >= y,
            '<=': lambda x, y: x <= y,
            '==': lambda x, y: x == y,
            '!=': lambda x, y: x != y,
            '^': math.pow,
            'in': lambda x, y: x in y,
        },
        'unary': {
            '-': lambda x: -x,
        },
    },
}


def is_expr(token):
    return token.startswith(EXPRESSION_START)

def is_stmt(token, type_=None):
    """
    Is this unparsed token a statement ? If type_ is not None, is it a statement of the given type ?

    >>> STATEMENT_START = "{%"
    >>> is_stmt("{% if %}", "if")
    True
    >>> is_stmt("{{ if %}", "if")
    False
    """
    if token.startswith(STATEMENT_START):
        if type_ == None:
            return True
        else:
            return token.split()[1].lower() == type_.lower()
    else:
        return False

def find_next_else(tokens, index):
    """
    >>> l = ['{% if age >= 18 %}', '{% if age >= 65 %}', 'senior', '{% else %}', '{% endif %}', \
    '{% if age >= 21 %}', 'can drink', '{% else %}', '{% endif %}', \
    '{% else  %}', '{%  if moon == "full" %}', 'yup, full', '{% else%}', '{% endif %}', '{% endif %}']
    >>> find_next_else(l, 1)
    9
    >>> l = ['{% if age >= 18 %}', '{% if age >= 65 %}', 'senior', '{% else %}', '{% endif %}', '{% else %}', '{% endif %}']
    >>> find_next_else(l, 1)
    5

    The straightforward case
    >>> l = ['{% if age >= 18 %}', 'adult', '{% else %}', '{% endif %}']
    >>> find_next_else(l, 1)
    2
    """
    open_ifs = 0
    for ix, token in enumerate(tokens[index:]):
        if is_stmt(token, "if"):
            open_ifs += 1
        if is_stmt(token, "endif"):
            open_ifs -= 1
        if open_ifs <= 0 and is_stmt(token, "else"):
            return index + ix
    return -1

def find_next_endif(tokens, index):
    """
    >>> l = ['{% if age >= 18 %}', '{% if age >= 65 %}', 'senior', '{% else %}', '{% endif %}', \
    '{% if age >= 21 %}', 'can drink', '{% else %}', '{% endif %}', \
    '{% else %}', '{% endif %}']
    >>> find_next_endif(l, 1)
    10
    >>> l = ['{% if age >= 18 %}', '{% if age >= 65 %}', 'senior', '{% else %}', '{% endif %}', '{% else %}', '{% endif %}']
    >>> find_next_endif(l, 1)
    6

    The straightforward case
    >>> l = ['{% if age >= 18 %}', 'adult', '{% else %}', '{% endif %}']
    >>> find_next_endif(l, 1)
    3
    """
    open_ifs = 0
    for ix, token in enumerate(tokens[index:]):
        if is_stmt(token, "if"):
            open_ifs += 1
        elif is_stmt(token, "endif"):
            open_ifs -= 1
            if open_ifs == 0:
                continue
        if open_ifs <= 0 and is_stmt(token, "endif"):
            return index + ix
    return -1


def tokenize(template):
    """Tokenize the text template
    This is the first step of the template engine.

    The tokenize function uses the TOKEN_REGEX to split the text template into a list of strings containing:
        * string constants
        * expressions ( "{{ name }}")
        * statements ( "{% if %}" or "{% for %}" or others )

    >>> TOKEN_REGEX.split("You are {% if age >= 18 %}old enough{% else %}not old enough{% endif %}!")
    ['You are ', '{% if age >= 18 %}', 'old enough', '{% else %}', 'not old enough', '{% endif %}', '!']

    Note that the regex split leaves empty strings before or after a tag:
    >>> TOKEN_REGEX.split("{% if age >= 18 %}old enough!{% else %}not old enough!{% endif %}")
    ['', '{% if age >= 18 %}', 'old enough!', '{% else %}', 'not old enough!', '{% endif %}', '']

    >>> tokenize("")
    []

    Simple string interpolation
    >>> tokenize("Hello there, {{ Name }}!")
    ['Hello there, ', '{{ Name }}', '!']
    >>> tokenize("{{ Name }}")
    ['{{ Name }}']

    Conditionals
    >>> tokenize("You are {% if age >= 18 %}old enough{% else %}not old enough{% endif %}!")
    ['You are ', '{% if age >= 18 %}', 'old enough', '{% else %}', 'not old enough', '{% endif %}', '!']
    >>> tokenize("You are {% if age >= 18 %}old enough{% else %}{% endif %}!")
    ['You are ', '{% if age >= 18 %}', 'old enough', '{% else %}', '{% endif %}', '!']

    Calculations
    >>> tokenize('You need {{12 - apple_count}} until you have a round dozen')
    ['You need ', '{{12 - apple_count}}', ' until you have a round dozen']

    Loops
    >>> tokenize('After, you can call {% for friend in friends %}{{friend}},{% endfor %} to help us eat.')
    ['After, you can call ', '{% for friend in friends %}', '{{friend}}', ',', '{% endfor %}', ' to help us eat.']

    Combined Statements
    >>> tokenize('You are {% if age >= 18 %}old enough and you have enough friends: {% for friend in friends %}{{friend}},{% endfor %}\
{% else %}not old enough{% endif %}!')
    ['You are ', '{% if age >= 18 %}', 'old enough and you have enough friends: ', '{% for friend in friends %}', '{{friend}}', ',', '{% endfor %}', '{% else %}', 'not old enough', '{% endif %}', '!']
    """

    if len(template) == 0:
        return []

    tokens = TOKEN_REGEX.split(template)

    # For some reason, TOKEN_REGEX.split leaves an empty string before and after template tags, if the tags are at the beginning or the end.
    # Let's filter these. Incidentally, this will also filter all other empty strings, like and empty else block. So the parser will have to handle this.
    tokens = [token for token in tokens if token]

    return tokens

def parse(tokens):
    """Parse the tokenized template.
    Transforms the flat list of tokens into a list-of-trees structure, respecting blocks. 
    This structure is known in the literature as an AST (abstract syntax tree).

    >>> parse([])
    []

    Flat things stay flat. Strings stay strings, expressions and statements get transformed into a tuple
    >>> parse(['Hello there, ', '{{ Name }}', '!'])
    ['Hello there, ', ('Name',), '!']

    Calculations
    >>> parse(['You need ', '{{12 - apple_count}}', ' until you have a round dozen'])
    ['You need ', (12, '-', 'apple_count'), ' until you have a round dozen']

    Conditionals
    >>> parse(['You are ', '{% if age >= 18 %}', 'old enough', '{% else %}', 'not old enough', '{% endif %}', '!'])
    ['You are ', ('if', ('age', '>=', 18), 'old enough', 'not old enough'), '!']
    >>> parse(['You are ', '{% if age >= 18 %}', 'old enough', '{% else %}', '{% endif %}', '!'])
    ['You are ', ('if', ('age', '>=', 18), 'old enough', ''), '!']

    For loops
    >>> parse(['After, you can call ', '{% for friend in friends %}', '{{friend}}', ',', '{% endfor %}', ' to help us eat.'])
    ['After, you can call ', ('for', ['friend', 'in', 'friends'], [('friend',), ',']), ' to help us eat.']

    Some statements open blocks that can contain expressions or statements
    >>> parse(['You are ', '{% if age >= 18 %}', 'old enough and you have enough friends: ', '{% for friend in friends %}', '{{friend}}', ',', '{% endfor %}', '{% else %}', 'not old enough', '{% endif %}', '!'])
    ['You are ', ('if', ('age', '>=', 18), ['old enough and you have enough friends: ', ('for', ['friend', 'in', 'friends'], [('friend',), ','])], 'not old enough'), '!']

    We can nest statements
    >>> parse(['Condition one ', '{% if age >= 18 %}', "is true, let's see: ", '{% if age >= 65 %}', ' yes you are a senior', '{% else %}', '{% endif %}', '{% else %}', '{% endif %}'])
    ['Condition one ', ('if', ('age', '>=', 18), ["is true, let's see: ", ('if', ('age', '>=', 65), ' yes you are a senior', '')], '')]
    >>> parse(['Condition one ', '{% if age >= 18 %}', "is true, let's loop: ", '{% for friend in friends %}',\
    '{% if friend == "Superman" %}', "wow, Superman, you have powerful friends!", '{% else %}', '{{friend}}', ',', '{% endif %}', '{% endfor %}', '{% else %}', 'not old enough', '{% endif %}', '!'])
    ['Condition one ', ('if', ('age', '>=', 18), ["is true, let's loop: ", ('for', ['friend', 'in', 'friends'], ('if', ('friend', '==', '"Superman"'), 'wow, Superman, you have powerful friends!', [('friend',), ',']))], 'not old enough'), '!']

    Some statements do not open blocks:
    >>> parse(['{% extends base.tmpl %}', 'Hello there!'])
    [('extends', ('base.tmpl',)), 'Hello there!']

    """
    # Let's go from tokenized (flat list of tokens) to AST

    if len(tokens) == 0:
        return []

    parsed = []

    def parse_expr(token, tokens, index):
        subtokens = token.split()
        def make_int(token):
            # @TODO This only processes ints, why not floats and other numerical types ?
            if token.isdigit():
                token = int(token)
            return token
        subtokens = [make_int(subtoken) for subtoken in subtokens]
        return tuple(subtokens)

    def unpack_len_one_list(l):
        if isinstance(l, list):
            if len(l) == 1:
                return l[0]
            # If empty list, it's an empty block, so return ""
            elif len(l) == 0:
                return ""
        return l

    def parse_stmt(token, tokens, index):
        subtokens = token.split()
        statement, params = subtokens[0], subtokens[1:]
        if statement == "if":
            params = parse([EXPRESSION_START + " ".join(params) + EXPRESSION_END])
            params = unpack_len_one_list(params)
            next_else_ = tokens[index:].index(STATEMENT_START + " else " + STATEMENT_END)
            next_else = find_next_else(tokens, index+1)
            conseq = tokens[index+1:next_else]
            conseq = parse(conseq)
            conseq = unpack_len_one_list(conseq)
            next_endif_ = tokens[index:].index(STATEMENT_START + " endif " + STATEMENT_END)
            next_endif = find_next_endif(tokens, index+1)
            alt = tokens[next_else+1:next_endif]
            alt = parse(alt)
            alt = unpack_len_one_list(alt)
            index = next_endif
            return index, tuple([statement, params, conseq, alt])
        elif statement == "for":
            next_endfor = tokens[index:].index(STATEMENT_START + " endfor " + STATEMENT_END)
            conseq = tokens[index+1:index+next_endfor]
            conseq = parse(conseq)
            conseq = unpack_len_one_list(conseq)
            index += next_endfor
            return index, tuple([statement, params, conseq])
        return index, tuple([statement, tuple(params)])

    index = 0
    while index < len(tokens):
        token = tokens[index]
        if is_expr(token):
            # Remove start and end tokens
            token = token[len(EXPRESSION_START):-len(EXPRESSION_END)]
            parsed.append(parse_expr(token, tokens, index))
        elif is_stmt(token):
            # Remove start and end tokens
            token = token[len(STATEMENT_START):-len(STATEMENT_END)]
            index, parsed_token = parse_stmt(token, tokens, index)
            parsed.append(parsed_token)
        else: # Must be a string constant, just append it
            parsed.append(token)
        index += 1

    return parsed


def is_parsed_token_a_statement(parsed_token):
    return parsed_token[0] in _GLOBAL_ENV['statements']

def is_parsed_token_an_expression(parsed_token):
    return not is_parsed_token_a_statement(parsed_token)

def eval_expression(exp, data_model):
    """
    For the purpose of simplicity, we won't handle nested expressions. Only simple bunary and unary expressions.
    Writing a nested exp evaluator is out-of-scope for now.
    >>> data = {"name": "Eva", "age": 23, "apple_count": 5, "friends": ["Billy", "John", "Emily"]}
    >>> eval_expression(('name',), data)
    'Eva'
    >>> eval_expression(('age',), data)
    23
    >>> eval_expression((12, '-', 'apple_count',), data)
    7
    >>> eval_expression(('Hello ', '+', 'name',), data)
    'Hello Eva'
    >>> eval_expression((3, '^', 2,), data)
    9.0
    >>> eval_expression(('age', '>=', 18,), data)
    True
    """
    # First step, replace variables by their values:
    exp = [data_model[elem] if elem in data_model else elem for elem in exp]
    if len(exp) == 3:
        # Binary operation
        left_hand = exp[0]
        op = exp[1]
        right_hand = exp[2]
        if op not in _GLOBAL_ENV['operators']['binary']:
            raise ValueError("Unknown binary operator: %s" % op)
        op = _GLOBAL_ENV['operators']['binary'][op]
        exp = [op(left_hand, right_hand)]
    elif len(exp) == 2:
        # Unary operation
        op = exp[0]
        right_hand = exp[1]
        if op not in _GLOBAL_ENV['operators']['unary']:
            raise ValueError("Unknown unary operator: %s" % op)
        op = _GLOBAL_ENV['operators']['binary'][op]
        exp = [op(right_hand)]
    
    return exp[0]

def eval_if_statement(*params, **kparams):
    cond = params[0]
    conseq = params[1]
    alt = params[2]
    data_model = {} if 'data_model' not in kparams else kparams['data_model']
    cond = eval_expression(cond, data_model)
    if cond:
        return eval_(conseq, data_model)
    else:
        return eval_(alt, data_model)

_GLOBAL_ENV['statements']['if'] = eval_if_statement

def eval_for_statement(*params, **kparams):
    for_ = params[0]
    if len(for_) != 3 or for_[1] != 'in':
        raise ValueError("Unknown for clause: %s " % str(for_))
    loop = params[1]
    data_model = {} if 'data_model' not in kparams else kparams['data_model']
    result = []
    elem_name = for_[0]
    elem_name_present_in_data_model = elem_name in data_model
    if elem_name_present_in_data_model:
        old_elem_in_data_model = data_model[elem_name]
    for elem in data_model[for_[2]]:
        data_model[elem_name] = elem
        result.append(eval_(loop, data_model))
    if elem_name_present_in_data_model:
        data_model[elem_name] = old_elem_in_data_model
    else:
        del data_model[elem_name]
        
    return ''.join(result)

_GLOBAL_ENV['statements']['for'] = eval_for_statement

def eval_extends_statement(*params, **kparams):
    parent = params[0]
    data_model = {} if 'data_model' not in kparams else kparams['data_model']
    return ""

_GLOBAL_ENV['statements']['extends'] = eval_extends_statement

def eval_statement(stmt, data_model):
    """
    For the purpose of simplicity, we won't handle nested expressions. Only simple bunary and unary expressions.
    Writing a nested exp evaluator is out-of-scope for now.
    >>> data = {"age": 23, "friends": ["Billy", "John", "Emily"]}
    >>> eval_statement(('len', 'friends'), data)
    3
    """
    # First step, replace variables by their values:
    stmt = [data_model[elem] if type(elem) != list and elem in data_model else elem for elem in stmt]
    procedure = _GLOBAL_ENV['statements'][stmt[0]]

    return procedure(*stmt[1:], data_model=data_model)

def eval_(parsed_template, data_model=None):
    """ This is the last step of the engine pipeline. Using the data model, this evaluates the parsed template, producing a flat string.

    >>> eval_([])
    ''

    Calculations and variables
    >>> data = {"name": "Eva", "age": 23, "apple_count": 5, "friends": ["Billy", "John", "Emily"]}
    >>> eval_(['Hello ', ('name',), ', what a fine age, ', ('age',), ', to be baking apple pies. You need ', (12, '-', 'apple_count'), ' more apples until you have a round dozen.'], data)
    'Hello Eva, what a fine age, 23, to be baking apple pies. You need 7 more apples until you have a round dozen.'

    Conditionals
    >>> data['age'] = 17
    >>> eval_(['You are ', ('if', ('age', '>=', 18), 'old enough', 'not old enough'), '!'], data)
    'You are not old enough!'
    >>> data['age'] = 23
    >>> eval_(['You are ', ('if', ('age', '>=', 18), ['old enough, ', ('name',)], ''), '!'], data)
    'You are old enough, Eva!'

    For loops
    >>> eval_(['After, you can call ', ('for', ('friend', 'in', 'friends'), [('friend',), ', ']), 'to help us eat.'], data)
    'After, you can call Billy, John, Emily, to help us eat.'
    >>> eval_(['After, you can call ', ('for', ['friend', 'within', 'friends'], [('friend',), ',']), ' to help us eat.'], data)
    Traceback (most recent call last):
      ...
    ValueError: Unknown for clause: ['friend', 'within', 'friends'] 

    Some statements open blocks that can contain expressions or statements
    >>> eval_(['You are ', ('if', ('age', '>=', 18), ['old enough and you have enough friends: ', ('for', ['friend', 'in', 'friends'], [('friend',), ', '])], 'not old enough'), '!'], data)
    'You are old enough and you have enough friends: Billy, John, Emily, !'

    We can nest statements
    >>> parse(['Condition one ', '{% if age >= 18 %}', "is true, let's see: ", '{% if age >= 65 %}', ' yes you are a senior', '{% else %}', '{% endif %}', '{% else %}', '{% endif %}'])
    ['Condition one ', ('if', ('age', '>=', 18), ["is true, let's see: ", ('if', ('age', '>=', 65), ' yes you are a senior', '')], '')]
    >>> parse(['Condition one ', '{% if age >= 18 %}', "is true, let's loop: ", '{% for friend in friends %}',\
    '{% if friend == "Superman" %}', "wow, Superman, you have powerful friends!", '{% else %}', '{{friend}}', ',', '{% endif %}', '{% endfor %}', '{% else %}', 'not old enough', '{% endif %}', '!'])
    ['Condition one ', ('if', ('age', '>=', 18), ["is true, let's loop: ", ('for', ['friend', 'in', 'friends'], ('if', ('friend', '==', '"Superman"'), 'wow, Superman, you have powerful friends!', [('friend',), ',']))], 'not old enough'), '!']

    Some statements do not open blocks:
    >>> eval_([('extends', ('base.tmpl',)), 'Hello there!'])
    'Hello there!'

    """
    data_model = {} if data_model is None else data_model
    evaluated = []
    for elem in parsed_template:
        if type(elem) == list:
            evaluated_element = eval_(elem, data_model)
        elif type(elem) == str or type(elem) == int:
            evaluated_element = elem
        elif type(elem) == tuple and is_parsed_token_a_statement(elem):
            evaluated_element = eval_statement(elem, data_model)
        elif type(elem) == tuple and is_parsed_token_an_expression(elem):
            evaluated_element = str(eval_expression(elem, data_model))
        else:
            raise Exception("Cannot evaluate parsed token, unknown type: %s" % str(elem))
            
        evaluated.append(evaluated_element)
        
    
    return "".join(evaluated)


class Template(object):
    """ This class is the public API of the template engine. """

    def __init__(self, file_):
        self.file_ = file_
        self.template = file_.read()
        self.parsed_template = None

    def render(self, data_model=None):
        tokenized = tokenize(self.template)
        if self.parsed_template is None:
            self.parsed_template = parse(tokenized)
        return eval_(self.parsed_template, data_model)

    def __str__(self):
        return self.render()


if __name__ == "__main__":
    """ DOCTEST FTW """
    import doctest
    doctest.testmod()

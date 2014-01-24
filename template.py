"""
This is a toy template engine, following the specification on http://pythonpracticeprojects.com/templating-engine.html

The template engine is a compiler, so it has the three classic steps of a compile pipeline:
 - tokenize
 - parse
 - eval
Each step is implemented in a separate function which has the same name as the step.
"""

import re


EXPRESSION_START = "{{"
EXPRESSION_END = "}}"
STATEMENT_START = "{%"
STATEMENT_END = "%}"
TOKEN_REGEX = re.compile(r"(%s.*?%s|%s.*?%s)" % (EXPRESSION_START, EXPRESSION_END, STATEMENT_START, STATEMENT_END))


def is_expr(token):
    return token.startswith(EXPRESSION_START)

def is_stmt(token, type_=None):
    """
    Is this a statement ? If type_ is not None, is it a statement of the given type ?

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

def eval_(parsed_template, data_model=None):
    """ This is the last step of the engine pipeline. Using the data model, this evaluates the parsed template, producing a flat string.

    >>> data = {"name": "Eva", "age": 23, "apple_count": 5, "friends": ["Billy", "John", "Emily"]}
    >>> eval_(['Hello ', ('name',), ', what a fine age, ', ('age',), ', to be baking apple pies. You need ', (12, '-', 'apple_count'), ' until you have a round dozen.'], data)
    'Hello Eva, what a fine age, 23, to be baking apple pies. You need 7 more apples until you have a round dozen.'

    """
    data_model = {} if data_model is None else data_model
    
    return str(parsed_template)


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

import ply.lex as lex
import ply.yacc as yacc
from typing import Dict, Any, List
from dataclasses import dataclass


# ============================================================================
# LEXER
# ============================================================================

# Reserved words
reserved = {
    'policy': 'POLICY',
    'when': 'WHEN',
    'then': 'THEN',
    'and': 'AND',
    'or': 'OR',
    'not': 'NOT',
    'true': 'TRUE',
    'false': 'FALSE',
    'action': 'ACTION',
    'block': 'BLOCK',
    'allow': 'ALLOW',
    'log': 'LOG',
    'alert': 'ALERT',
    'reason': 'REASON',
    'input': 'INPUT',
    'output': 'OUTPUT',
    'context': 'CONTEXT',
    'user': 'USER',
}

# Token list
tokens = [
    'STRING',
    'NUMBER',
    'FLOAT',
    'IDENTIFIER',
    'LPAREN',
    'RPAREN',
    'LBRACE',
    'RBRACE',
    'COMMA',
    'COLON',
    'DOT',
    'GT',
    'LT',
    'GTE',
    'LTE',
    'EQ',
    'NEQ',
] + list(reserved.values())

# Token rules
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','
t_COLON = r':'
t_DOT = r'\.'
t_GT = r'>'
t_LT = r'<'
t_GTE = r'>='
t_LTE = r'<='
t_EQ = r'=='
t_NEQ = r'!='

def t_FLOAT(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_STRING(t):
    r'"[^"]*"'
    t.value = t.value[1:-1]  # Remove quotes
    return t

def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value.lower(), 'IDENTIFIER')
    return t

t_ignore = ' \t'

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_COMMENT(t):
    r'\#.*'
    pass  # Ignore comments

def t_error(t):
    raise SyntaxError(f"Illegal character '{t.value[0]}' at line {t.lineno}")


# ============================================================================
# AST NODES
# ============================================================================

@dataclass
class PolicyAST:
    """Root AST node for a policy"""
    name: str
    conditions: 'ConditionNode'
    actions: List['ActionNode']


@dataclass
class ConditionNode:
    """AST node for conditions"""
    type: str  # 'and', 'or', 'not', 'comparison', 'function_call'
    left: Any = None
    right: Any = None
    operator: str = None
    value: Any = None


@dataclass
class ActionNode:
    """AST node for actions"""
    action_type: str  # 'block', 'allow', 'log', 'alert'
    params: Dict[str, Any] = None


@dataclass
class FunctionCallNode:
    """AST node for function calls"""
    object: str  # 'input', 'output', 'context', 'user'
    method: str
    args: List[Any]


# ============================================================================
# PARSER
# ============================================================================

def p_policy(p):
    '''policy : POLICY STRING LBRACE when_clause then_clause RBRACE'''
    p[0] = PolicyAST(name=p[2], conditions=p[4], actions=p[5])

def p_when_clause(p):
    '''when_clause : WHEN LBRACE condition RBRACE'''
    p[0] = p[3]

def p_then_clause(p):
    '''then_clause : THEN LBRACE action_list RBRACE'''
    p[0] = p[3]

def p_condition_and(p):
    '''condition : condition AND condition'''
    p[0] = ConditionNode(type='and', left=p[1], right=p[3])

def p_condition_or(p):
    '''condition : condition OR condition'''
    p[0] = ConditionNode(type='or', left=p[1], right=p[3])

def p_condition_not(p):
    '''condition : NOT condition'''
    p[0] = ConditionNode(type='not', left=p[2])

def p_condition_comparison(p):
    '''condition : expression comparison_op expression'''
    p[0] = ConditionNode(
        type='comparison',
        left=p[1],
        operator=p[2],
        right=p[3]
    )

def p_condition_function(p):
    '''condition : function_call'''
    p[0] = ConditionNode(type='function_call', value=p[1])

def p_condition_paren(p):
    '''condition : LPAREN condition RPAREN'''
    p[0] = p[2]

def p_comparison_op(p):
    '''comparison_op : GT
                     | LT
                     | GTE
                     | LTE
                     | EQ
                     | NEQ'''
    p[0] = p[1]

def p_expression_property(p):
    '''expression : INPUT DOT IDENTIFIER
                  | OUTPUT DOT IDENTIFIER
                  | CONTEXT DOT IDENTIFIER
                  | USER DOT IDENTIFIER'''
    p[0] = FunctionCallNode(object=p[1], method=p[3], args=[])

def p_expression_number(p):
    '''expression : NUMBER
                  | FLOAT'''
    p[0] = p[1]

def p_expression_string(p):
    '''expression : STRING'''
    p[0] = p[1]

def p_expression_bool(p):
    '''expression : TRUE
                  | FALSE'''
    p[0] = p[1].lower() == 'true'

def p_function_call(p):
    '''function_call : INPUT DOT IDENTIFIER LPAREN arg_list RPAREN
                     | OUTPUT DOT IDENTIFIER LPAREN arg_list RPAREN
                     | CONTEXT DOT IDENTIFIER LPAREN arg_list RPAREN
                     | USER DOT IDENTIFIER LPAREN arg_list RPAREN'''
    p[0] = FunctionCallNode(object=p[1], method=p[3], args=p[5])

def p_arg_list(p):
    '''arg_list : arg_list COMMA expression
               | expression
               | empty'''
    if len(p) == 4:
        p[0] = p[1] + [p[3]]
    elif len(p) == 2 and p[1] is not None:
        p[0] = [p[1]]
    else:
        p[0] = []

def p_action_list(p):
    '''action_list : action_list action
                   | action'''
    if len(p) == 3:
        p[0] = p[1] + [p[2]]
    else:
        p[0] = [p[1]]

def p_action(p):
    '''action : ACTION COLON action_type
              | REASON COLON STRING
              | IDENTIFIER COLON expression'''
    if p[1] == 'action':
        p[0] = ActionNode(action_type=p[3])
    elif p[1] == 'reason':
        p[0] = ActionNode(action_type='reason', params={'message': p[3]})
    else:
        p[0] = ActionNode(action_type='param', params={p[1]: p[3]})

def p_action_type(p):
    '''action_type : BLOCK
                   | ALLOW
                   | LOG
                   | ALERT'''
    p[0] = p[1]

def p_empty(p):
    '''empty :'''
    p[0] = None

def p_error(p):
    if p:
        raise SyntaxError(f"Syntax error at '{p.value}', line {p.lineno}")
    else:
        raise SyntaxError("Syntax error at end of input")


class DSLParser:
    """Parser for Sentinel Policy DSL"""

    def __init__(self):
        self.lexer = lex.lex()
        self.parser = yacc.yacc()

    def parse(self, source: str) -> PolicyAST:
        """Parse DSL source code into AST"""
        return self.parser.parse(source, lexer=self.lexer)

    def compile(self, source: str) -> Dict[str, Any]:
        """Compile DSL to JSON policy config"""
        ast = self.parse(source)
        return self._ast_to_config(ast)

    def _ast_to_config(self, ast: PolicyAST) -> Dict[str, Any]:
        """Convert AST to policy_config JSON"""
        return {
            "name": ast.name,
            "dsl_version": "1.0",
            "conditions": self._condition_to_json(ast.conditions),
            "actions": [self._action_to_json(a) for a in ast.actions],
        }

    def _condition_to_json(self, cond: ConditionNode) -> Dict[str, Any]:
        """Convert condition node to JSON"""
        if cond.type in ('and', 'or'):
            return {
                "type": cond.type,
                "conditions": [
                    self._condition_to_json(cond.left),
                    self._condition_to_json(cond.right),
                ]
            }
        elif cond.type == 'not':
            return {
                "type": "not",
                "condition": self._condition_to_json(cond.left),
            }
        elif cond.type == 'comparison':
            return {
                "type": "comparison",
                "left": self._value_to_json(cond.left),
                "operator": cond.operator,
                "right": self._value_to_json(cond.right),
            }
        elif cond.type == 'function_call':
            return {
                "type": "function",
                "object": cond.value.object,
                "method": cond.value.method,
                "args": cond.value.args,
            }
        return {}

    def _value_to_json(self, value: Any) -> Any:
        """Convert value to JSON-serializable form"""
        if isinstance(value, FunctionCallNode):
            return {
                "type": "property",
                "object": value.object,
                "property": value.method,
            }
        return value

    def _action_to_json(self, action: ActionNode) -> Dict[str, Any]:
        """Convert action node to JSON"""
        result = {"type": action.action_type}
        if action.params:
            result["params"] = action.params
        return result
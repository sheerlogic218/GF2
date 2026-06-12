import re
import uuid

# pass
A = "(A+!B*C)*(Y+(C))"
B = "(A*C)+!(C*D)+(R+(S+!T))"
C = "A+((A+B)*D+(C*E))"
D = "A+(B*E)+!C+D+(A*B*C*A)"
E = "A*!G+B+(A+D*G+(G*A+D))+(C+D)*A*!C^X+G"
E2 = "A + ((B))"

# fail
F = "A)(B"
G = "A((+)B)"
G2 = "A(B)"
G3 = "A(B+C)"
H = "A)+((B)"


def separate_brackets(val):
    re_exp = re.compile(r"(\([a-zA-Z0-9+*^!\- ]*\))")

    if (l_brackets := val.count("(")) != (r_brackets := val.count(")")):
        raise SyntaxError(
            f"Invalid expression line, brackets do not match: {val}"
        )

    parts = re.split(re_exp, val)

    if len(parts) < l_brackets + 1:
        raise SyntaxError(
            f"Invalid expression line, brackets do not match: {val}"
        )

    parts_to_eval = {}
    depth = 0
    while len(parts) != 1:
        if depth >= 10**3:
            raise Exception("Depth error: Too many brackets")
        for i, part in enumerate(parts):
            if len(part.strip()) == 0:
                continue
            if part[0] == "(" and part[-1] == ")":
                # captures empty brackets
                if len(part[1:-1]) == 0:
                    pos = re.search(r"\(\)", val).span()
                    raise SyntaxError(
                        f"Invalid expression line, empty parenthesis: {val}\n {" " * (56 + pos[0]) + "^" * (pos[1] - pos[0])}"
                    )

                # captures single variables in brackets
                elif len(part[1:-1]) == 1:
                    if part[1] in "+*^!":
                        pos = re.search(r"\([+*^!]\)", val).span()
                        raise SyntaxError(
                            f"Invalid expression line, parenthesis around operator: {val}\n {" " * (66 + pos[0]) + "^" * (pos[1] - pos[0])}"
                        )
                    parts[i] = part[1:-1]
                    continue

                id = "00" + str(uuid.uuid4())
                parts[i] = id
                parts_to_eval[id] = part[1:-1]

        parts = re.split(re_exp, "".join(parts))
        depth += 1
    return parts[0], parts_to_eval


def process_expressions(expression: str, mapping: dict) -> list:
    or_gate_inputs = expression.strip("()").split("+")
    for or_input in or_gate_inputs:
        if mapping.get(or_input):
            or_input = mapping[or_input]
        print(or_input)
        and_gate_inputs = or_input.strip("()").split("*")
        print(and_gate_inputs)
        for and_input in and_gate_inputs:
            if mapping.get(and_input):
                and_input = mapping[and_input]

    return 9999


# expression, mappings = separate_brackets(G3)
#
# print(f"expression: {expression}")
# print(f"mappings:  {mappings}")
#
#
# print()
# print(process_expressions(expression, mappings))

this = "__gate__aghsdjkaghsd"
print(this.split("__")[1])

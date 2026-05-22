import re
import uuid

A = "(A+!B*C)*(Y+(C))+((((((((()))))))))"


def func1(val):
    re_exp = re.compile(r"(\([a-zA-Z0-9+*^!\- ]*\))")
    L_bracket = val.count("(")
    R_bracket = val.count(")")
    if L_bracket != R_bracket:
        raise SyntaxError(f"Invalid expression line, brackets do not match: {val}")

    parts = re.split(re_exp, val)
    parts_to_eval = {}
    depth = 0
    while len(parts) != 1:
        if depth >= 10**3:
            raise Exception("Depth error: Too many brackets")
        for i, part in enumerate(parts):
            if len(part.strip()) == 0:
                continue
            if part[0] == "(" and part[-1] == ")":
                if len(part[1:-1]) == 0:
                    pos = re.search(r"\(\)", val).span()
                    print(pos)
                    raise SyntaxError(
                        f"Invalid expression line, empty parenthesis: {val}\n {" "*(56+pos[0])+"^"*(pos[1]-pos[0])}"
                    )
                id = str(uuid.uuid4())
                parts[i] = id
                # process basic expression
                parts_to_eval[id] = part
        parts = "".join(parts)
        parts = re.split(re_exp, parts)
        depth += 1

    return parts, parts_to_eval


thing = func1(A)
print(thing[0])
print(thing[1])

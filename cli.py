import argparse
import re

from tracer import trace


class ParsingError(Exception):
    pass


def parse_expr(expr):
    expr = re.sub(r'\s+', '', expr)
    expr_parts = expr.split('.')

    if len(expr_parts) < 2:
        msg = 'got no module or no function in entry expression.'
        raise ParsingError(msg)

    mn = '.'.join(expr_parts[:-1])
    fcall = expr_parts[-1]

    if re.search(r'\(.*?\)', fcall) is None:
        msg = 'got no function call in entry expression.'
        raise ParsingError(msg)

    return mn, fcall


def cast_target(val, cast_func='str'):
    expr = f'{cast_func}({val})'
    try:
        val = eval(expr)
    except Exception as e:
        msg = f'while casting target as `{expr}` got exception `{e}`.'
        raise ParsingError(msg)

    return val


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('-e', type=str, help='entry function call expression.', required=True)
    arg_parser.add_argument('-t', type=str, help='target to trace.', required=True)
    arg_parser.add_argument('--o', type=str, help='report json file path.', default=None)
    arg_parser.add_argument('--ttype', type=str, help='target type cast function (default `str`).', default='str')
    arg_parser.add_argument('--d', type=int, help='enable debug', default=0)
    arg_parser.add_argument('--stack', type=int, help='enable stack tracking', default=0)
    args = arg_parser.parse_args()

    mn, fcall = parse_expr(args.e)
    target = cast_target(val=args.t, cast_func=args.ttype)
    debug = bool(args.d)
    track_stack = bool(args.stack)
    trace(mn=mn, fcall=fcall, targets=[target], report_fp=args.o, debug=debug, track_stack=track_stack)

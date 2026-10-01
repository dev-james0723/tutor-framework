import argparse,json
from .compiler import compile_existing
p=argparse.ArgumentParser(prog="caplin-lesson")
s=p.add_subparsers(dest="command",required=True)
c=s.add_parser("audit-existing");c.add_argument("root");c.add_argument("--output",required=True)
a=p.parse_args()
if a.command=="audit-existing": print(json.dumps(compile_existing(a.root,a.output),indent=2,ensure_ascii=False))

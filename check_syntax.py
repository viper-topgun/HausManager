import ast, sys, os

errors = []
for root, dirs, files in os.walk('backend'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fh:
                src = fh.read()
            try:
                ast.parse(src)
            except SyntaxError as e:
                errors.append(f'{path}: {e}')

if errors:
    print('ERRORS:', errors)
    sys.exit(1)
else:
    print('All Python files OK')

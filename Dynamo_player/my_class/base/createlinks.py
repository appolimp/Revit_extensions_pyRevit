import os
import shutil


def main():
    exclude_names = ('all', 'wip')
    script_dirs = [n for n in os.listdir('..') if n not in exclude_names and os.path.isdir(n)]
    try:
        shutil.rmtree('all')
    except FileNotFoundError:
        pass
    os.makedirs('all')
    for script_dir in script_dirs:
        files = [n for n in os.listdir(script_dir) if n.endswith('.dyn') or n.endswith('.py')]
        for file in files:
            try:
                os.link(os.path.join(script_dir, file), os.path.join('all', file))
            except FileExistsError:
                pass


if __name__ == '__main__':
    main()

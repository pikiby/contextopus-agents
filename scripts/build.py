"""Build a folder-module ZIP using only source files, never live state."""
import argparse
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, default=root / 'dist/contextopus-agents-0.4.0.zip')
args = parser.parse_args()
args.output.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for source in sorted((root / 'module').rglob('*')):
        if source.is_symlink():
            raise ValueError('Symlink in module source')
        if source.is_file() and '__pycache__' not in source.parts and source.suffix != '.pyc':
            archive.write(source, 'agents/' + source.relative_to(root / 'module').as_posix())
    for source in sorted((root / 'docs').glob('*.md')):
        archive.write(source, 'agents/docs/' + source.name)
    for name in ('README.md', 'LICENSE', 'NOTICE', 'install.sh', 'install.ps1'):
        if (root / name).is_file():
            archive.write(root / name, 'agents/' + name)
print(args.output)

from pathlib import Path

p = Path(__file__).resolve().parent.parent / "main.py"
text = p.read_text(encoding="utf-8-sig")
p.write_text(text, encoding="utf-8", newline="\n")
print("rewrote", p)

import os

path = "gui/components.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replaces = [
    (
        "        p.drawPath(path)",
        "        p.drawPath(path)\n        p.end()"
    ),
    (
        "        p.drawPath(path_bg)",
        "        p.drawPath(path_bg)\n        p.end()"
    ),
    (
        "        p.drawText(bx, by, bw, bh, Qt.AlignmentFlag.AlignCenter, f\"{int(self.current_val)}\")",
        "        p.drawText(bx, by, bw, bh, Qt.AlignmentFlag.AlignCenter, f\"{int(self.current_val)}\")\n        p.end()"
    ),
    (
        "        p.drawText(0, self.height() - 2, self.width(), 10, Qt.AlignmentFlag.AlignRight, \"REC\")",
        "        p.drawText(0, self.height() - 2, self.width(), 10, Qt.AlignmentFlag.AlignRight, \"REC\")\n        p.end()"
    ),
    (
        "            p.drawRect(bx, self.height() - h_bar, self.bar_w, h_bar)",
        "            p.drawRect(bx, self.height() - h_bar, self.bar_w, h_bar)\n        p.end()"
    ),
    (
        "        p.drawText(QRect(0,0,self.width(),self.height()), Qt.AlignmentFlag.AlignCenter, self.text)",
        "        p.drawText(QRect(0,0,self.width(),self.height()), Qt.AlignmentFlag.AlignCenter, self.text)\n        p.end()"
    ),
    (
        "        p.drawArc(r, r, w, w, start_angle, span_angle)",
        "        p.drawArc(r, r, w, w, start_angle, span_angle)\n        p.end()"
    ),
    (
        "        p.drawEllipse(self.rect())",
        "        p.drawEllipse(self.rect())\n        p.end()"
    ),
    (
        "            p.drawLine(gx, by, gx, by + bh)",
        "            p.drawLine(gx, by, gx, by + bh)\n        p.end()"
    ),
    (
        "            p.drawText(0, i * step, w, step, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)",
        "            p.drawText(0, i * step, w, step, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)\n        p.end()"
    )
]

for old, new in replaces:
    text = text.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Patch applied.")

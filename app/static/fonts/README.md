# Invoice PDF font

`NotoSansSC-Regular.ttf` is a static regular (weight 400) instance of
Google Fonts' Noto Sans SC variable font, retrieved on 2026-09-22.
It covers Latin and Simplified Chinese; fpdf2 embeds only the glyphs used
in each document.

Source font:
https://github.com/google/fonts/blob/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf

Source license:
https://github.com/google/fonts/blob/main/ofl/notosanssc/OFL.txt

The included `OFL.txt` is the SIL Open Font License 1.1, including the
original copyright notice. It permits embedding and redistribution.
The regular instance was made with the existing fontTools package:

```python
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

font = TTFont("NotoSansSC-variable.ttf")
instantiateVariableFont(font, {"wght": 400}, inplace=True)
font.save("NotoSansSC-Regular.ttf")
```

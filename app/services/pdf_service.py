"""PDF service: generates comic PDFs using FPDF2."""
import json
import logging
from pathlib import Path
from fpdf import FPDF
from PIL import Image as PILImage
from sqlalchemy.orm import Session
from app.models.comic import Comic
from app.models.panel import Panel
from app.utils.file_utils import export_pdf_path

import unicodedata
import re

logger = logging.getLogger(__name__)

FONT_FAMILY = "Helvetica"
PAGE_W, PAGE_H = 210, 297  # A4 mm
MARGIN = 12
IMG_W = PAGE_W - 2 * MARGIN
IMG_H = 90


# Comprehensive emoji-to-symbol dictionary
EMOJI_SYMBOL_MAP = {
    # Emoticons & Smiles
    "😀": ":D", "😃": ":D", "😄": ":D", "😁": ":D", "😆": "XD", "😅": ":')",
    "😂": ":'D", "🤣": "XD", "🥲": ":')", "🥹": ":')", "☺️": ":)", "😊": ":)",
    "😇": "(O:)", "🙂": ":)", "🙃": "(:", "😉": ";)", "😌": ":)", "😍": "<3",
    "🥰": "<3", "😘": ":*", "😗": ":*", "😙": ":*", "😚": ":*", "😋": ":P",
    "😛": ":P", "😝": "XP", "😜": ";P", "🤪": ":P", "🤨": ":/", "🧐": "[?]",
    "🤓": "[B)]", "😎": "8)", "🥸": "[8v]", "🤩": "[*_*]", "🥳": "[Party!]",
    "😏": ";)", "😒": ":(", "😞": ":(", "😔": ":(", "😟": ":(", "😕": ":/",
    "🙁": ":(", "☹️": ":(", "😣": ">_<", "😖": ">_<", "😫": "D:", "😩": "D:",
    "🥺": "(:_;)", "😢": ":'(", "😭": ":'((", "😮‍💨": "[Sigh]", "😤": ">:(",
    "😠": ">:(", "😡": "X(", "🤬": "#$%!", "🤯": "[MindBlown!]", "😳": "[o_o]",
    "🥵": "[Hot]", "🥶": "[Cold]", "😱": "[:O]", "😨": "[:(]", "😰": "[:'(]",
    "😥": "[:'(]", "😓": "[:(]", "🤗": "[Hugs]", "🤔": "[Thinking]", "🤫": "[Shh]",
    "🤥": "[Lie]", "😶": "[:|]", "😐": ":|", "😑": "-_-", "😯": ":O", "😦": ":o",
    "😧": "D:", "😮": ":O", "😲": ":O", "🥱": "[Yawn]", "😴": "[Zzz]", "🤤": "[Drool]",
    "😪": "[Sleepy]", "😵": "[X_X]", "😵‍💫": "[Dizzy]", "🤐": "[:-x]", "🤢": "[Sick]",
    "🤮": "[Barf]", "🤧": "[Achoo]", "😷": "[Mask]", "🤒": "[Sick]", "🤕": "[Injured]",
    "🤑": "[$_$]", "🤠": "[Cowboy]", "😈": ">:)", "👿": ">:(", "👹": "[Ogre]",
    "👺": "[Goblin]", "🤡": "[Clown]", "💩": "[Poop]", "👻": "[Ghost]", "💀": "[Skull]",
    "☠️": "[Skull]", "👽": "[Alien]", "👾": "[8-bit]", "🤖": "[Robot]", "🎃": "[Pumpkin]",
    "😺": ":3", "😸": ":3", "😹": ":'3", "😻": "<3", "😼": ";3", "😽": ":*3",
    "🙀": ":O3", "😿": ":'c", "😾": ">:c",

    # Hand Gestures & People
    "👋": "[Wave]", "🤚": "[Hand]", "🖐️": "[Hand]", "✋": "[Stop]", "🖖": "[Vulcan]",
    "👌": "[OK]", "🤌": "[ChefKiss]", "🤏": "[Pinch]", "✌️": "[Peace]", "🤞": "[FingersCrossed]",
    "🤟": "[Love]", "🤘": "[RockOn]", "🤙": "[CallMe]", "👈": "<-", "👉": "->",
    "👆": "[^]", "👇": "[v]", "👍": "[+1]", "👎": "[-1]", "✊": "[Fist]", "👊": "[Punch]",
    "👏": "[Clap]", "🙌": "[Hurray]", "🫶": "<3", "👐": "[OpenHands]", "🤲": "[Hands]",
    "🤝": "[Handshake]", "🙏": "[Pray]", "✍️": "[Writing]", "🤳": "[Selfie]", "💪": "[Strong]",
    "🦸": "[Hero]", "🦹": "[Villain]", "🧙": "[Wizard]", "🧚": "[Fairy]", "🧛": "[Vampire]",
    "🧜": "[Mermaid]", "🧝": "[Elf]", "🧞": "[Genie]", "🧟": "[Zombie]", "🥷": "[Ninja]",
    "🤴": "[Prince]", "👸": "[Princess]", "👑": "[Crown]", "👼": "[Angel]", "🧑‍🚀": "[Astronaut]",
    "🧑‍🎨": "[Artist]", "🧑‍💻": "[Hacker]", "🧑‍🔬": "[Scientist]", "👮": "[Police]", "🕵️": "[Detective]",

    # Animals
    "🐶": "[Dog]", "🐱": "[Cat]", "🐭": "[Mouse]", "🐹": "[Hamster]", "🐰": "[Rabbit]",
    "🦊": "[Fox]", "🐻": "[Bear]", "🐼": "[Panda]", "🐨": "[Koala]", "🐯": "[Tiger]",
    "🦁": "[Lion]", "🐮": "[Cow]", "🐷": "[Pig]", "🐸": "[Frog]", "🐵": "[Monkey]",
    "🐔": "[Chicken]", "🐧": "[Penguin]", "🐦": "[Bird]", "🐤": "[Chick]", "🦆": "[Duck]",
    "🦅": "[Eagle]", "🦉": "[Owl]", "🦇": "[Bat]", "🐺": "[Wolf]", "🐗": "[Boar]",
    "🐴": "[Horse]", "🦄": "[Unicorn]", "🐝": "[Bee]", "🐛": "[Bug]", "🦋": "[Butterfly]",
    "🐌": "[Snail]", "🐞": "[Ladybug]", "🐜": "[Ant]", "🕷️": "[Spider]", "🦂": "[Scorpion]",
    "🐢": "[Turtle]", "🐍": "[Snake]", "🦎": "[Lizard]", "🦖": "[T-Rex]", "🦕": "[Dino]",
    "🐙": "[Octopus]", "🦑": "[Squid]", "🦐": "[Shrimp]", "🦀": "[Crab]", "🐡": "[Fish]",
    "🐠": "[Fish]", "🐟": "[Fish]", "🐬": "[Dolphin]", "🐳": "[Whale]", "🐋": "[Whale]",
    "🦈": "[Shark]", "🐊": "[Croc]", "🐅": "[Tiger]", "🐆": "[Leopard]", "🦓": "[Zebra]",
    "🦍": "[Gorilla]", "🐘": "[Elephant]", "🦏": "[Rhino]", "🐪": "[Camel]", "🦒": "[Giraffe]",
    "🦘": "[Kangaroo]", "🐕": "[Dog]", "🐈": "[Cat]", "🐾": "[Pawprints]", "🐉": "[Dragon]",
    "🐲": "[Dragon]",

    # Nature & Sky
    "🌲": "[Tree]", "🌳": "[Tree]", "🌴": "[Palm]", "🌵": "[Cactus]", "🌾": "[Grass]",
    "🌿": "[Herb]", "☘️": "[Clover]", "🍀": "[Lucky4Leaf]", "🍁": "[MapleLeaf]", "🍂": "[Leaf]",
    "🍃": "[Leaves]", "🍄": "[Mushroom]", "🌸": "[Flower]", "🌹": "[Rose]", "🌻": "[Sunflower]",
    "🌼": "[Flower]", "🌷": "[Tulip]", "🌱": "[Sprout]", "🌙": "[Moon]", "☀️": "[Sun]",
    "⭐": "[*]", "🌟": "[*]", "💫": "[*]", "✨": "*", "⚡": "[Lightning]", "☄️": "[Comet]",
    "💥": "[BOOM!]", "🔥": "[FIRE!]", "🌪️": "[Tornado]", "🌈": "[Rainbow]", "⛅": "[Cloudy]",
    "☁️": "[Cloud]", "🌧️": "[Rain]", "🌨️": "[Snow]", "🌩️": "[Thunder]", "❄️": "[Snowflake]",
    "☃️": "[Snowman]", "🌊": "[Wave]", "💧": "[Drop]", "🪐": "[Planet]",

    # Objects, Weapons, Magic, Tech
    "🚀": "[ROCKET]", "🛸": "[UFO]", "🛰️": "[Satellite]", "🗡️": "[SWORD]", "⚔️": "[BATTLE]",
    "🛡️": "[SHIELD]", "🏹": "[BOW]", "🪄": "[WAND]", "🔮": "[ORB]", "💎": "[GEM]",
    "📜": "[SCROLL]", "📖": "[BOOK]", "📚": "[BOOKS]", "🚪": "[DOOR]", "城堡": "[CASTLE]", "🏰": "[CASTLE]",
    "🏙️": "[CITY]", "🌆": "[CITY]", "🌃": "[NIGHT]", "🏠": "[HOUSE]", "⛺": "[TENT]",
    "🏝️": "[ISLAND]", "🌋": "[VOLCANO]", "⛰️": "[MOUNTAIN]", "🏕️": "[CAMP]", "🏖️": "[BEACH]",
    "🗺️": "[MAP]", "🧭": "[COMPASS]", "🚗": "[CAR]", "🏎️": "[RACECAR]", "🚢": "[SHIP]",
    "⛵": "[BOAT]", "⚓": "[ANCHOR]", "💣": "[BOMB]", "🧨": "[DYNAMITE]", "🧪": "[POTION]",
    "🧬": "[DNA]", "🔬": "[MICROSCOPE]", "🔭": "[TELESCOPE]", "💡": "[IDEA!]", "🔦": "[LIGHT]",
    "🎁": "[GIFT]", "🎈": "[BALLOON]", "🏆": "[TROPHY]", "🥇": "[#1]", "🥈": "[#2]",
    "🥉": "[#3]", "🎯": "[TARGET]", "🎨": "[ART]", "🖌️": "[BRUSH]", "🎭": "[THEATER]",
    "🎤": "[MIC]", "🎧": "[HEADPHONES]", "🎵": "[MUSIC]", "🎶": "[NOTES]", "🎸": "[GUITAR]",
    "🎹": "[PIANO]", "🥁": "[DRUMS]", "🎬": "[ACTION]", "🎮": "[GAME]", "🎲": "[DICE]",
    "🗝️": "[KEY]", "🔑": "[KEY]", "🔒": "[LOCKED]", "🔓": "[UNLOCKED]", "🔔": "[BELL]",
    "📢": "[ALERT]", "📣": "[ANNOUNCE]", "💬": "[SPEECH]", "💭": "[THINK]", "💤": "[ZZZ]",
    "💰": "[COINS]", "💵": "[CASH]", "📦": "[BOX]", "✉️": "[LETTER]", "📄": "[DOC]",
    "📌": "[PIN]", "✂️": "[CUT]", "✏️": "[PENCIL]", "🔍": "[SEARCH]", "🔎": "[SEARCH]",
    "❤️": "<3", "🧡": "<3", "💛": "<3", "💚": "<3", "💙": "<3", "💜": "<3", "🖤": "<3",
    "🤍": "<3", "💔": "</3", "❣️": "!", "💕": "<3<3", "💖": "<3*", "💘": "-<3->",
    "❌": "[X]", "⭕": "[O]", "❗": "!", "❕": "!", "❓": "?", "❔": "?", "‼️": "!!",
    "⁉️": "!?", "💯": "[100]", "⚠️": "[WARN]", "✅": "[V]", "➕": "+", "➖": "-",
    "➗": "/", "✖️": "x", "™️": "(TM)", "©️": "(C)", "®️": "(R)", "📭": "[EmptyMail]",
}


def _safe_text(text: str | None) -> str:
    """Safely convert text for standard FPDF fonts (Latin-1 / ASCII safe) with emoji-to-symbol translation."""
    if text is None:
        return ""
    text = str(text)

    # Convert typographical and common special characters
    replacements = {
        "\u2014": " - ",  # em dash
        "\u2013": "-",    # en dash
        "\u2012": "-",    # figure dash
        "\u2015": " - ",  # horizontal bar
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote
        "\u201a": "'",    # low single quote
        "\u201b": "'",    # high single reversed quote
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u201e": '"',    # low double quote
        "\u2026": "...",  # ellipsis
        "\u2022": "*",    # bullet
        "\u00b7": "|",    # middle dot
        "\u00a9": "(c)",  # copyright
        "\u00ae": "(R)",  # registered
        "\u2122": "(TM)", # trademark
        "\u2605": "*",    # black star
        "\u2606": "*",    # white star
        "\u2713": "[v]",  # check mark
        "\u2714": "[v]",  # check mark
        "\u2716": "[x]",  # cross
        "\u2717": "[x]",  # cross
        "\u2192": "->",   # right arrow
        "\u2190": "<-",   # left arrow
        "\u2194": "<->",  # left-right arrow
        "\u2020": "+",    # dagger
        "\u2021": "++",   # double dagger
        "\u00ab": '<<',   # left-pointing double angle quotation mark
        "\u00bb": '>>',   # right-pointing double angle quotation mark
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)

    # Convert known emojis to symbols / text tags
    for emoji_char, symbol_repl in EMOJI_SYMBOL_MAP.items():
        if emoji_char in text:
            text = text.replace(emoji_char, symbol_repl)

    # Convert any other remaining emojis / non-ascii symbols using unicodedata or general stripper
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010ffff"
        "\u2600-\u27bf"
        "\ufe00-\ufe0f"
        "\u200d"
        "\u2300-\u23ff"
        "\u2b50-\u2b55"
        "\u203c-\u2049"
        "]+",
        flags=re.UNICODE,
    )
    text = emoji_pattern.sub(" ", text)

    # Clean latin-1 encoding
    try:
        text = text.encode("latin-1", errors="replace").decode("latin-1")
    except Exception:
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

    # Clean up multi-spaces
    text = re.sub(r' +', ' ', text)
    return text.strip()


class ComicPDF(FPDF):
    """Custom FPDF subclass with ComicCraft styling."""

    def header(self):
        pass  # handled per page

    def footer(self):
        self.set_y(-10)
        self.set_font(FONT_FAMILY, "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, _safe_text(f"ComicCraft - Page {self.page_no()}"), align="C")



class PDFService:
    """Creates PDF exports of comics."""

    def export_comic_to_pdf(self, db: Session, comic: Comic) -> Path:
        """Generate a PDF for the comic and return its file path."""
        panels = sorted(comic.panels, key=lambda p: p.panel_number)
        output_path = export_pdf_path(comic.id)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pdf = ComicPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(MARGIN, MARGIN, MARGIN)

        # ── Cover page ───────────────────────────────────────────────────────
        pdf.add_page()
        pdf.set_fill_color(255, 248, 237)  # #FFF8ED
        pdf.rect(0, 0, PAGE_W, PAGE_H, "F")

        # Accent bar
        pdf.set_fill_color(244, 185, 66)  # #F4B942
        pdf.rect(0, 0, PAGE_W, 8, "F")

        pdf.set_y(40)
        pdf.set_font(FONT_FAMILY, "B", 28)
        pdf.set_text_color(23, 23, 23)
        pdf.cell(0, 12, "COMICCRAFT", align="C", ln=True)

        pdf.set_font(FONT_FAMILY, "", 11)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "AI Comic Story Creator", align="C", ln=True)

        pdf.ln(16)
        pdf.set_font(FONT_FAMILY, "B", 18)
        pdf.set_text_color(23, 23, 23)
        pdf.multi_cell(0, 9, _safe_text(comic.title), align="C")

        if comic.chapter_number > 1:
            pdf.set_font(FONT_FAMILY, "I", 12)
            pdf.set_text_color(232, 93, 4)
            pdf.cell(0, 8, f"Chapter {comic.chapter_number}", align="C", ln=True)

        pdf.ln(12)
        pdf.set_draw_color(230, 222, 210)
        pdf.line(MARGIN + 20, pdf.get_y(), PAGE_W - MARGIN - 20, pdf.get_y())
        pdf.ln(8)

        # Meta info
        meta = [
            ("Character", comic.character_name),
            ("Setting", comic.setting),
            ("Tone", comic.tone),
            ("Art Style", comic.art_style),
        ]
        for label, value in meta:
            pdf.set_font(FONT_FAMILY, "B", 9)
            pdf.set_text_color(150, 100, 30)
            pdf.cell(35, 6, label + ":", ln=False)
            pdf.set_font(FONT_FAMILY, "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.cell(0, 6, _safe_text(str(value)), ln=True)

        if comic.summary:
            pdf.ln(8)
            pdf.set_font(FONT_FAMILY, "I", 9)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, _safe_text(comic.summary))

        # Bottom accent
        pdf.set_fill_color(232, 93, 4)
        pdf.rect(0, PAGE_H - 8, PAGE_W, 8, "F")

        # ── Panel pages ──────────────────────────────────────────────────────
        for panel in panels:
            pdf.add_page()
            pdf.set_fill_color(255, 248, 237)
            pdf.rect(0, 0, PAGE_W, PAGE_H, "F")

            # Panel header bar
            pdf.set_fill_color(23, 23, 23)
            pdf.rect(0, 0, PAGE_W, 10, "F")
            pdf.set_y(2)
            pdf.set_font(FONT_FAMILY, "B", 8)
            pdf.set_text_color(244, 185, 66)
            pdf.cell(0, 6, _safe_text(f"PANEL {panel.panel_number}  |  {comic.title.upper()}"), align="C")

            y = 14
            pdf.set_y(y)

            # Panel title
            pdf.set_font(FONT_FAMILY, "B", 14)
            pdf.set_text_color(23, 23, 23)
            pdf.multi_cell(0, 7, _safe_text(panel.title))
            y = pdf.get_y() + 3

            # Panel image
            if panel.image_path and Path(panel.image_path).exists():
                try:
                    img_path = str(panel.image_path)
                    with PILImage.open(img_path) as img:
                        w, h = img.size
                        # Convert RGBA/P to RGB if needed to prevent PDF rendering errors
                        if img.mode in ("RGBA", "P", "LA"):
                            rgb_img = img.convert("RGB")
                            temp_rgb_path = output_path.parent / f"temp_{panel.panel_number}_{panel.id[:8]}.jpg"
                            rgb_img.save(temp_rgb_path, "JPEG", quality=95)
                            img_path = str(temp_rgb_path)
                    aspect = h / w if w > 0 else 0.75
                    img_h = min(IMG_W * aspect, IMG_H)
                    pdf.image(img_path, x=MARGIN, y=y, w=IMG_W, h=img_h)
                    y += img_h + 4
                except Exception as e:
                    logger.warning(f"Could not embed image for panel {panel.panel_number}: {e}")
                    pdf.set_font(FONT_FAMILY, "I", 8)
                    pdf.set_text_color(150, 150, 150)
                    pdf.set_y(y)
                    pdf.cell(0, 6, "[Image not available]", align="C", ln=True)
                    y += 8
            else:
                pdf.set_font(FONT_FAMILY, "I", 8)
                pdf.set_text_color(180, 180, 180)
                pdf.set_y(y)
                pdf.cell(0, 6, "[Image not generated]", align="C", ln=True)
                y += 8

            pdf.set_y(y)

            # Narration box
            if panel.narration:
                pdf.set_fill_color(255, 240, 213)
                pdf.set_draw_color(244, 185, 66)
                pdf.set_font(FONT_FAMILY, "I", 9)
                pdf.set_text_color(80, 50, 10)
                narration_text = _safe_text(panel.narration)
                pdf.multi_cell(0, 5, narration_text, border=1, fill=True)
                y = pdf.get_y() + 3
                pdf.set_y(y)

            # Scene description
            if panel.scene_description:
                pdf.set_font(FONT_FAMILY, "", 8)
                pdf.set_text_color(100, 100, 100)
                pdf.multi_cell(0, 4.5, _safe_text(panel.scene_description))
                y = pdf.get_y() + 2
                pdf.set_y(y)

            # Dialogue
            if panel.dialogue:
                if isinstance(panel.dialogue, list):
                    dialogue_list = panel.dialogue
                elif isinstance(panel.dialogue, str):
                    try:
                        dialogue_list = json.loads(panel.dialogue)
                    except (json.JSONDecodeError, TypeError):
                        dialogue_list = []
                else:
                    dialogue_list = []

                if isinstance(dialogue_list, list):
                    for line in dialogue_list:
                        if not isinstance(line, dict):
                            continue
                        char = _safe_text(str(line.get("character", "")))
                        text = _safe_text(str(line.get("text", "")))
                        pdf.set_fill_color(240, 240, 255)
                        pdf.set_draw_color(200, 200, 240)
                        pdf.set_font(FONT_FAMILY, "B", 8)
                        pdf.set_text_color(40, 40, 120)
                        pdf.cell(25, 5, char + ":", ln=False)
                        pdf.set_font(FONT_FAMILY, "", 8)
                        pdf.set_text_color(40, 40, 40)
                        pdf.multi_cell(0, 5, '"' + text + '"', border="B")
                        y = pdf.get_y() + 1
                        pdf.set_y(y)

            # Bottom accent
            pdf.set_fill_color(232, 93, 4)
            pdf.rect(0, PAGE_H - 8, PAGE_W, 8, "F")

        pdf.output(str(output_path))
        logger.info(f"PDF exported to {output_path}")
        return output_path

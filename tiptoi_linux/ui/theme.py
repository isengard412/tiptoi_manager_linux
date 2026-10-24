"""Colors and stylesheet for the tiptoi-Manager look-alike UI.

The palette was measured from the original application's UI atlas; see
docs/reference/style-guide.md. All values here are our own reimplementation -
no original artwork is bundled.
"""

from __future__ import annotations

# --- palette (docs/reference/style-guide.md) ----------------------------------------------

BRAND_ORANGE = "#F7A900"
BRAND_ORANGE_DEEP = "#F59C00"
HEADER_ORANGE = "#FBD47F"
HEADER_ORANGE_SOFT = "#FCE3AC"
FRAME_TEAL = "#497A88"
TEXT_GRAY = "#5B5B5B"
NAV_ACTIVE = "#CEB5D5"
ICON_GREEN = "#ABDCCB"
ICON_PINK = "#F0A7A9"
ICON_BLUE = "#B1D2DE"
ICON_ORANGE = "#FACD7F"
ERROR_RED = "#D80C18"
BG_WHITE = "#FFFFFF"
BG_LIGHT = "#F2F2F2"
BORDER_LIGHT = "#E4E4E4"

UI_FONT_FAMILY = "Nunito Sans, Nunito, Segoe UI, Cantarell, DejaVu Sans, sans-serif"


def build_style_sheet() -> str:
    """QSS for the whole shell. Widgets are targeted by objectName / dynamic property."""
    return f"""
    QMainWindow, QWidget {{
        font-family: {UI_FONT_FAMILY};
        color: {FRAME_TEAL};
        background: {BG_WHITE};
    }}

    /* --- header ------------------------------------------------------ */
    HeaderBar {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {HEADER_ORANGE}, stop:1 {HEADER_ORANGE_SOFT});
        border-bottom: 1px solid {BRAND_ORANGE};
    }}
    HeaderBar QLabel {{ background: transparent; }}
    QLabel#LogoText {{
        color: {BG_WHITE};
        font-size: 30px;
        font-weight: 800;
        letter-spacing: -1px;
    }}
    QLabel#LogoR {{ color: {BG_WHITE}; font-size: 12px; font-weight: 600; }}
    QLabel#LogoSub {{ color: {FRAME_TEAL}; font-size: 11px; }}

    QPushButton#OptionsButton {{
        background: {BG_WHITE};
        color: {FRAME_TEAL};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 14px;
        padding: 5px 14px;
        font-size: 13px;
    }}
    QPushButton#OptionsButton:hover {{ border-color: {BRAND_ORANGE}; color: {BRAND_ORANGE_DEEP}; }}

    /* --- pen card in the header --------------------------------------- */
    PenCard {{
        background: {BG_WHITE};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 10px;
    }}
    PenCard QLabel {{ background: transparent; }}
    QLabel#PenCardTitle {{ color: {TEXT_GRAY}; font-size: 12px; font-weight: 600; }}
    QLabel#PenStatusPill {{
        border-radius: 9px;
        color: {BG_WHITE};
        font-size: 11px;
        font-weight: 700;
        padding: 2px 10px;
        background: {ICON_GREEN};
    }}
    QLabel#PenFreePill {{
        border-radius: 9px;
        color: {FRAME_TEAL};
        font-size: 11px;
        font-weight: 600;
        padding: 2px 10px;
        background: {HEADER_ORANGE};
    }}

    /* --- nav rail ------------------------------------------------------ */
    NavRail {{ background: {BG_WHITE}; border-right: 1px solid {BORDER_LIGHT}; }}
    QToolButton#NavItem {{
        background: transparent;
        border: none;
        color: {FRAME_TEAL};
        text-align: left;
        padding: 6px 10px;
        font-size: 12.5px;
        font-weight: 600;
        border-radius: 20px;
    }}
    QToolButton#NavItem[active="true"] {{
        background: {NAV_ACTIVE};
        color: {BG_WHITE};
    }}
    QToolButton#NavItem:hover[active="false"] {{ background: {BG_LIGHT}; }}

    QPushButton#SearchButton {{
        border: none;
        background: transparent;
        padding: 0;
    }}

    /* --- search -------------------------------------------------------- */
    QLineEdit#SearchInput {{
        border: 2px solid {BRAND_ORANGE};
        border-radius: 17px;
        padding: 6px 14px;
        font-size: 14px;
        color: {FRAME_TEAL};
        background: {BG_WHITE};
        selection-background-color: {HEADER_ORANGE};
    }}
    QLabel#ResultCount {{ color: {FRAME_TEAL}; font-size: 13px; font-weight: 600; background: transparent; }}

    /* --- pill buttons ---------------------------------------------------- */
    QPushButton[buttonRole="primary"] {{
        background: {BRAND_ORANGE};
        color: {BG_WHITE};
        border: none;
        border-radius: 15px;
        padding: 6px 18px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton[buttonRole="primary"]:hover {{ background: {BRAND_ORANGE_DEEP}; }}
    QPushButton[buttonRole="primary"]:disabled {{ background: {BG_LIGHT}; color: #B5B5B5; }}
    QPushButton[buttonRole="secondary"] {{
        background: {BG_WHITE};
        color: {BRAND_ORANGE_DEEP};
        border: 2px solid {BRAND_ORANGE};
        border-radius: 15px;
        padding: 5px 16px;
        font-size: 13px;
        font-weight: 700;
    }}
    QPushButton[buttonRole="secondary"]:hover {{ background: {HEADER_ORANGE_SOFT}; }}
    QPushButton[buttonRole="secondary"]:disabled {{
        color: #B5B5B5; border-color: {BORDER_LIGHT}; background: {BG_WHITE};
    }}

    /* --- tables / lists -------------------------------------------------- */
    QTableView {{
        background: {BG_WHITE};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 8px;
        gridline-color: {BG_LIGHT};
        selection-background-color: {HEADER_ORANGE_SOFT};
        selection-color: {FRAME_TEAL};
        font-size: 13px;
    }}
    QHeaderView::section {{
        background: {BG_WHITE};
        color: {TEXT_GRAY};
        border: none;
        border-bottom: 2px solid {BRAND_ORANGE};
        padding: 6px;
        font-weight: 700;
    }}
    QListWidget {{
        background: {BG_WHITE};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 8px;
        font-size: 13px;
        padding: 4px;
    }}
    QListWidget::item {{ padding: 4px 6px; border-radius: 6px; }}
    QListWidget::item:selected {{ background: {HEADER_ORANGE_SOFT}; color: {FRAME_TEAL}; }}

    QListView#productGrid {{ background: {BG_WHITE}; border: none; outline: none; }}
    QListView#productGrid::item {{ border: none; }}
    QListView#productGrid::item:selected {{ background: {HEADER_ORANGE_SOFT}; border-radius: 10px; }}

    QPushButton#CategoryChip {{
        background: {BG_WHITE};
        border: 1px solid {BORDER_LIGHT};
        border-radius: 14px;
        padding: 4px 14px;
        font-size: 12px;
        font-weight: 600;
        color: {FRAME_TEAL};
    }}
    QPushButton#CategoryChip:hover {{ border-color: {BRAND_ORANGE}; }}
    QPushButton#CategoryChip:checked {{
        background: {BRAND_ORANGE};
        border-color: {BRAND_ORANGE};
        color: {BG_WHITE};
    }}

    /* --- storage / progress bars -------------------------------------- */
    QProgressBar {{
        border: none;
        border-radius: 8px;
        background: {BG_LIGHT};
        height: 16px;
        font-size: 11px;
        font-weight: 700;
        color: {FRAME_TEAL};
        text-align: center;
    }}
    QProgressBar::chunk {{ background: {BRAND_ORANGE}; border-radius: 8px; }}

    /* --- footer ---------------------------------------------------------- */
    FooterBar {{ background: {BG_WHITE}; border-top: 1px solid {BORDER_LIGHT}; }}
    FooterBar QLabel {{ background: transparent; }}
    QLabel#FooterInfo {{ color: {TEXT_GRAY}; font-size: 11px; }}
    QPushButton#FooterLink {{
        background: transparent; border: none; color: {TEXT_GRAY};
        font-size: 11px; text-decoration: underline;
    }}
    QPushButton#FooterLink:hover {{ color: {BRAND_ORANGE_DEEP}; }}

    QLabel#Placeholder {{ color: {TEXT_GRAY}; font-size: 14px; }}

    QMessageBox {{ background: {BG_WHITE}; }}
    """

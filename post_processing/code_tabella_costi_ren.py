import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import textwrap

# === Parametri grafico ===
fig, ax = plt.subplots(figsize=(11, 3))
ax.set_xlim(0, 9)
ax.set_ylim(0, 3)
ax.axis("off")

# === Colori ===
frame_color = "#66c2d6"      # azzurro del bordo
title_color = "#08306b"      # blu scuro
subtitle_color = "#2171b5"   # blu medio
text_color = "black"

# === Disegno cornice principale ===
ax.add_patch(Rectangle((0, 0), 9, 3, 
                       edgecolor=frame_color, facecolor="white", lw=2.5))

# === Linee divisorie interne ===
ax.plot([3, 3], [0, 3], color=frame_color, lw=1.5, ls="--")
ax.plot([6, 6], [0, 3], color=frame_color, lw=1.5, ls="--")

# === Dati aggiornati ===
sections = [
    {
        "icon": "PV/Wind",
        "title": "Technology Investment",
        "items": [
            ("PV modules:", "1093 $/kW"),
            ("Wind turbines:", "1333 $/kW")
        ]
    },
    {
        "icon": "Grid",
        "title": "Grid Connections",
        "items": [
            ("Depends on the specific locations:", 
             "The further from the grid, the higher the costs")
        ]
    },
    {
        "icon": "O&M",
        "title": "Yearly O&M",
        "items": [
            ("PV modules:", "15 $ y⁻¹/kW"),
            ("Wind turbines:", "35 $ y⁻¹/kW")
        ]
    }
]

# === Stampa testo nelle colonne ===
for i, sec in enumerate(sections):
    x_center = 1.5 + 3 * i
    
    # icona (ora semplice testo, puoi sostituire con PNG se vuoi)
    ax.text(x_center, 2.6, sec["icon"], fontsize=12, color=title_color, 
            ha="center", va="center", weight="bold")
    
    # titolo
    ax.text(x_center, 2.2, sec["title"], fontsize=12, color=title_color, 
            ha="center", va="center", weight="bold")
    
    # contenuto
    y_pos = 1.6
    for label, value in sec["items"]:
        if len(value) < 40:  # normale
            ax.text(x_center - 1.2, y_pos, label, fontsize=10, color=subtitle_color, 
                    ha="left", va="center", weight="bold")
            ax.text(x_center + 1.2, y_pos, value, fontsize=10, color=text_color, 
                    ha="right", va="center")
            y_pos -= 0.4
        else:  # text wrapping per descrizioni lunghe
            wrapped = textwrap.fill(value, 35)
            ax.text(x_center, y_pos, f"{label}\n{wrapped}", 
                    fontsize=10, color=text_color, ha="center", va="top")
            y_pos -= 0.8

# === Salva immagine ===
plt.tight_layout()
plt.savefig("clusters_economic_parameters.png", dpi=300, bbox_inches="tight")
plt.show()

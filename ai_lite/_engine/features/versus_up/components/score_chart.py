import flet as ft
from contexthub.ui.flet.tokens import COLORS, RADII, SPACING
from contexthub.ui.flet.layout import section_card

PRODUCT_COLORS = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4"]

class ScoreChart(ft.Container):
    def __init__(self, products, scores):
        super().__init__()
        self.products = products
        self.scores = scores
        self.visible = False
        self.build_chart()

    def build_chart(self):
        if not self.products or not self.scores:
            self.content = ft.Container()
            return

        max_score = max(self.scores.values()) if self.scores else 1.0
        if max_score <= 0: max_score = 1.0

        bar_rows = []
        for i, p in enumerate(self.products):
            score = self.scores.get(p[0], 0.0)
            color = PRODUCT_COLORS[i % len(PRODUCT_COLORS)]
            percentage = min(1.0, score / max_score)
            
            bar_rows.append(
                ft.Row([
                    ft.Container(width=80, content=ft.Text(p[2], size=10, color=COLORS["text"], no_wrap=True, overflow=ft.TextOverflow.ELLIPSIS)),
                    ft.Stack([
                        ft.Container(height=16, expand=True, bgcolor=COLORS["app_bg"], border_radius=RADII["sm"]),
                        ft.Container(
                            height=16, width=1, expand=max(1, int(percentage * 100)),
                            bgcolor=color, border_radius=RADII["sm"],
                            animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT_QUART)
                        ),
                    ], expand=True),
                    ft.Container(width=40, alignment=ft.alignment.Alignment(1, 0), content=ft.Text(f"{score:.1f}", size=11, weight=ft.FontWeight.BOLD, color=color))
                ], spacing=SPACING["xs"])
            )

        self.content = section_card("Score Comparison", ft.Column(bar_rows, spacing=4, tight=True))

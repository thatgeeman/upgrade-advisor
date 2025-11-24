from __future__ import annotations

from typing import Iterable

from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class Christmas(Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.red,
        secondary_hue: colors.Color | str = colors.green,
        neutral_hue: colors.Color | str = colors.stone,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_lg,
        text_size: sizes.Size | str = sizes.text_lg,
        font: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Poppins"),
            fonts.GoogleFont("Nunito"),
            "ui-sans-serif",
            "sans-serif",
        ),
        font_mono: fonts.Font | str | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("JetBrains Mono"),
            "ui-monospace",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )
        super().set(
            body_background_fill=(
                "radial-gradient(rgba(255, 255, 255, 0.6) 2px, transparent 2px) 0 0/26px 26px, "
                "radial-gradient(rgba(239, 68, 68, 0.55) 2px, transparent 2px) 13px 13px/26px 26px, "
                "rgba(15, 42, 29, 0.92)"
            ),
            body_background_fill_dark=(
                "radial-gradient(rgba(243, 244, 246, 0.52) 2px, transparent 2px) 0 0/26px 26px, "
                "radial-gradient(rgba(248, 113, 113, 0.48) 2px, transparent 2px) 13px 13px/26px 26px, "
                "rgba(5, 20, 13, 0.94)"
            ),
            background_fill_primary="rgba(255, 255, 255, 0.92)",
            background_fill_primary_dark="rgba(12, 22, 17, 0.9)",
            background_fill_secondary="rgba(255, 255, 255, 0.78)",
            background_fill_secondary_dark="rgba(18, 33, 24, 0.85)",
            border_color_accent="#f2c94c",
            border_color_accent_dark="#eab308",
            color_accent="#f2c94c",
            color_accent_soft="rgba(242, 201, 76, 0.15)",
            color_accent_soft_dark="rgba(234, 179, 8, 0.2)",
            block_background_fill="rgba(255, 255, 255, 0.86)",
            block_background_fill_dark="rgba(14, 26, 20, 0.92)",
            block_border_color="*primary_200",
            block_border_color_dark="*primary_700",
            block_radius="16px",
            block_shadow="0 20px 60px rgba(0, 0, 0, 0.22)",
            block_shadow_dark="0 24px 70px rgba(0, 0, 0, 0.55)",
            block_title_background_fill="linear-gradient(90deg, rgba(239, 68, 68, 0.12), rgba(34, 197, 94, 0.1))",
            block_title_background_fill_dark="linear-gradient(90deg, rgba(239, 68, 68, 0.18), rgba(34, 197, 94, 0.16))",
            block_title_text_color="*primary_800",
            block_title_text_color_dark="*primary_100",
            block_title_text_weight="700",
            button_primary_background_fill="linear-gradient(120deg, *primary_500, #f59e0b 80%)",
            button_primary_background_fill_hover="linear-gradient(120deg, #34d399, #bbf7d0 80%)",
            button_primary_background_fill_dark="linear-gradient(120deg, *primary_600, #d97706 80%)",
            button_primary_background_fill_hover_dark="linear-gradient(120deg, #10b981, #34d399 80%)",
            button_primary_text_color="white",
            button_primary_text_color_dark="white",
            button_primary_shadow="0 10px 40px rgba(0, 0, 0, 0.25)",
            button_primary_shadow_hover="0 12px 45px rgba(0, 0, 0, 0.3)",
            button_primary_shadow_dark="0 10px 40px rgba(0, 0, 0, 0.5)",
            button_primary_shadow_hover_dark="0 12px 45px rgba(0, 0, 0, 0.58)",
            button_secondary_background_fill="linear-gradient(120deg, *secondary_400, *secondary_600)",
            button_secondary_background_fill_hover="linear-gradient(120deg, *secondary_300, *secondary_500)",
            button_secondary_background_fill_dark="linear-gradient(120deg, *secondary_500, *secondary_700)",
            button_secondary_background_fill_hover_dark="linear-gradient(120deg, *secondary_400, *secondary_600)",
            button_secondary_text_color="white",
            button_secondary_text_color_dark="white",
            button_secondary_shadow="0 8px 30px rgba(0, 0, 0, 0.25)",
            button_secondary_shadow_dark="0 8px 30px rgba(0, 0, 0, 0.45)",
            button_transition="all 180ms ease-in-out",
            input_background_fill="rgba(255, 255, 255, 0.94)",
            input_background_fill_dark="rgba(13, 24, 18, 0.94)",
            input_border_color="*primary_200",
            input_border_color_hover="*primary_300",
            input_border_color_focus="#f2c94c",
            input_border_color_dark="*primary_800",
            input_border_color_hover_dark="*primary_700",
            input_border_color_focus_dark="#facc15",
            input_shadow="0 6px 30px rgba(0, 0, 0, 0.1)",
            input_shadow_dark="0 6px 30px rgba(0, 0, 0, 0.45)",
            panel_background_fill="rgba(255, 255, 255, 0.82)",
            panel_background_fill_dark="rgba(14, 25, 19, 0.9)",
            panel_border_color="*primary_200",
            panel_border_color_dark="*primary_800",
            slider_color="*secondary_400",
            slider_color_dark="*secondary_500",
            checkbox_label_background_fill="rgba(255, 255, 255, 0.8)",
            checkbox_label_background_fill_dark="rgba(17, 30, 24, 0.9)",
            checkbox_label_border_color="*secondary_200",
            checkbox_label_border_color_dark="*secondary_700",
            checkbox_label_text_color="*secondary_800",
            checkbox_label_text_color_dark="*secondary_50",
            link_text_color="#b91c1c",
            link_text_color_hover="#f59e0b",
            link_text_color_dark="#fbbf24",
            link_text_color_hover_dark="#f59e0b",
            loader_color="*primary_400",
            loader_color_dark="*primary_300",
            button_large_padding="28px",
        )


christmas = Christmas()

"""Presentation-only constraints for the Rating history plot.

Preserve useful hover/camera interactions, but disable zoom and pan so mobile
touch gestures cannot hide the whole timeline behind a tiny axis range.
"""


PLOTLY_CONFIG = {
    "scrollZoom": False,
    "doubleClick": False,
    "displaylogo": False,
    "displayModeBar": True,
    "responsive": True,
    "modeBarButtonsToRemove": [
        "zoom2d", "pan2d", "select2d", "lasso2d",
        "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d",
    ],
}

# Upstream Codeforces rank palette, in ascending rating order.
RATING_BANDS = (
    (float("-inf"), 1200, "#CCCCCC"),
    (1200, 1400, "#77FF77"),
    (1400, 1600, "#77DDFF"),
    (1600, 1900, "#AAAAFF"),
    (1900, 2100, "#FF88FF"),
    (2100, 2300, "#FFCC88"),
    (2300, 2400, "#FFBB55"),
    (2400, 3000, "#FF7777"),
    (3000, float("inf"), "#AA0000"),
)


def lock_rating_chart(fig):
    """Lock both axes to the data range and paint the visible rating bands."""
    fig.update_layout(dragmode=False)
    fig.update_xaxes(autorange=True, fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    ratings = [rating for trace in fig.data if trace.y is not None for rating in trace.y]
    if ratings:
        low, high = min(ratings), max(ratings)
        padding = max(50, (high - low) * 0.06)
        y_min, y_max = low - padding, high + padding
        # Fit the viewport to the traces so band shapes cannot expand the axis.
        fig.update_yaxes(autorange=False, range=[y_min, y_max])
        shapes = []
        for lower, upper, color in RATING_BANDS:
            y0, y1 = max(lower, y_min), min(upper, y_max)
            if y0 < y1:
                shapes.append(dict(
                    type="rect", xref="paper", x0=0, x1=1, yref="y",
                    y0=y0, y1=y1, fillcolor=color, opacity=0.15,
                    layer="below", line_width=0,
                ))
        fig.update_layout(shapes=shapes)
    return fig

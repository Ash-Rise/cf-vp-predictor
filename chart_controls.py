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


def lock_rating_chart(fig):
    """Lock both axes to the full auto-fitted data range; keep hover enabled."""
    fig.update_layout(dragmode=False)
    fig.update_xaxes(autorange=True, fixedrange=True)
    fig.update_yaxes(autorange=True, fixedrange=True)
    return fig

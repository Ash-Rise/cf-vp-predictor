import unittest

import plotly.graph_objects as go

from chart_controls import PLOTLY_CONFIG, lock_rating_chart


class RatingChartTests(unittest.TestCase):
    def test_zoom_and_pan_disabled_but_hover_still_available(self):
        fig = go.Figure(go.Scatter(x=[1, 2, 3], y=[100, 200, 300]))
        lock_rating_chart(fig)
        self.assertIs(fig.layout.dragmode, False)
        self.assertIs(fig.layout.xaxis.fixedrange, True)
        self.assertIs(fig.layout.yaxis.fixedrange, True)
        self.assertIs(fig.layout.xaxis.autorange, True)
        self.assertIs(fig.layout.yaxis.autorange, True)
        self.assertIs(PLOTLY_CONFIG["scrollZoom"], False)
        self.assertIs(PLOTLY_CONFIG["doubleClick"], False)
        self.assertNotIn("staticPlot", PLOTLY_CONFIG)
        self.assertIn("zoom2d", PLOTLY_CONFIG["modeBarButtonsToRemove"])
        self.assertIn("pan2d", PLOTLY_CONFIG["modeBarButtonsToRemove"])


if __name__ == "__main__":
    unittest.main()

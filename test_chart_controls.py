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
        self.assertIs(fig.layout.yaxis.autorange, False)
        self.assertIs(PLOTLY_CONFIG["scrollZoom"], False)
        self.assertIs(PLOTLY_CONFIG["doubleClick"], False)
        self.assertNotIn("staticPlot", PLOTLY_CONFIG)
        self.assertIn("zoom2d", PLOTLY_CONFIG["modeBarButtonsToRemove"])
        self.assertIn("pan2d", PLOTLY_CONFIG["modeBarButtonsToRemove"])

    def test_background_uses_visible_bands_without_expanding_rating_axis(self):
        fig = go.Figure([
            go.Scatter(y=[0, 1500]),
            go.Scatter(y=[1650, 1737]),
        ])
        lock_rating_chart(fig)
        y_min, y_max = fig.layout.yaxis.range
        self.assertLess(y_min, 0)
        self.assertGreater(y_max, 1737)
        self.assertLess(y_max, 1900)
        self.assertEqual(
            [(s.y0, s.y1, s.fillcolor) for s in fig.layout.shapes],
            [
                (y_min, 1200, "#CCCCCC"), (1200, 1400, "#77FF77"),
                (1400, 1600, "#77DDFF"), (1600, y_max, "#AAAAFF"),
            ],
        )
        self.assertTrue(all(s.layer == "below" for s in fig.layout.shapes))


if __name__ == "__main__":
    unittest.main()

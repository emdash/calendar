import cairo

## general options

width = 600
height = 400
day_width = width / 8
hour_height = 50

## colors

text_color = cairo.SolidPattern(0, 0, 0, .75)

# grid
grid_line_color = cairo.SolidPattern(1, 1, 1)
grid_bg_color = cairo.SolidPattern(0.8, 0.8, 0.8)
comfort_line_color = cairo.SolidPattern(0.55, 0.55, 0.55)

# headings
heading_outline_color = cairo.SolidPattern(1, 1, 1)
weekday_bg_color = cairo.SolidPattern(0.75, 0.85, 0.75)
weekend_bg_color = cairo.SolidPattern(0.75, 0.75, 0.85)
hour_heading_color = cairo.SolidPattern(0.75, 0.75, 0.75)
corner_bg_color = cairo.SolidPattern(0.75, 0.75, 0.75)

# selection
handle_bg_color = cairo.SolidPattern(0.0, 0.0, 0.0, 0.55)
handle_arrow_color = cairo.SolidPattern(1, 1, 1)
marquee_fill_color = cairo.SolidPattern(0, 0, 0, 0.25)
marquee_text_color = cairo.SolidPattern(0, 0, 0, 0.75)

# default event color
default_event_bg_color = cairo.SolidPattern(0.55, 0.55, 0.55)
default_event_text_color = cairo.SolidPattern(0, 0, 0)
